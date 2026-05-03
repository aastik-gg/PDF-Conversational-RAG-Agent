"""Gemini-backed generation with strict system grounding."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app import config
from app.utils.prompts import GROUNDING_SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

_RETRIEVAL_TRANSLATE_SYSTEM = """You translate the user's question into concise English for searching an English-language document index.
Preserve product and business terms (e.g. "North Star metric", OKR, KPI) using their usual English spellings.
Output ONLY the English search phrase or question, one line. No quotes, labels, or explanation."""

_TRANSLATE_TEMPERATURE = 0.0


def get_llm() -> ChatGoogleGenerativeAI:
    if not config.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set in the environment.")
    return ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.1,
    )


def translate_question_for_retrieval(non_english_question: str) -> str:
    """One-shot English paraphrase for vector search only (not grounded on PDF)."""
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=_TRANSLATE_TEMPERATURE,
    )
    messages = [
        SystemMessage(content=_RETRIEVAL_TRANSLATE_SYSTEM),
        HumanMessage(content=non_english_question),
    ]
    response = llm.invoke(messages)
    text = (getattr(response, "content", None) or "").strip()
    if not text:
        raise RuntimeError("Translation for retrieval returned empty text.")
    # Strip accidental wrapping quotes
    text = text.strip().strip('"').strip("'")
    logger.info("Retrieval translation length: %d", len(text))
    return text


def generate_grounded_answer(context: str, question: str) -> str:
    """Invoke Gemini with strict system instructions and user context + question."""
    llm = get_llm()
    user_content = build_user_prompt(context=context, question=question)
    messages = [
        SystemMessage(content=GROUNDING_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]
    response = llm.invoke(messages)
    text = (getattr(response, "content", None) or "").strip()
    if not text:
        raise RuntimeError("The language model returned an empty response.")
    logger.info("LLM response length: %d characters", len(text))
    return text
