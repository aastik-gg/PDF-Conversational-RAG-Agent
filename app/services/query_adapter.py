"""Adapt user queries for cross-lingual retrieval (e.g. Hindi Q vs English PDF)."""

from __future__ import annotations

import logging

from app.services.llm import translate_question_for_retrieval

logger = logging.getLogger(__name__)

# Devanagari block (Hindi, Marathi, etc.)
_DEVANAGARI = "\u0900", "\u097f"


def is_hindi_dominant(text: str) -> bool:
    """
    Heuristic: enough Devanagari vs Latin letters to treat as Hindi for retrieval.

    English-only questions stay on the original string for embedding search.
    """
    dev = lat = 0
    for ch in text:
        if _DEVANAGARI[0] <= ch <= _DEVANAGARI[1]:
            dev += 1
        elif "A" <= ch <= "Z" or "a" <= ch <= "z":
            lat += 1
    if dev < 3:
        return False
    return dev >= lat


def prepare_retrieval_query(user_question: str) -> tuple[str, bool]:
    """
    Return (query_for_faiss_search, translated).

    Hindi-heavy questions are translated to English so embeddings align with
    typical English PDF chunks; the caller still uses the original question
    for the final grounded answer (response language).
    """
    if not is_hindi_dominant(user_question):
        return user_question, False
    try:
        translated = translate_question_for_retrieval(user_question)
        if translated and translated.strip():
            logger.info(
                "Using English retrieval query (from Hindi): %s",
                translated[:200] + ("…" if len(translated) > 200 else ""),
            )
            return translated.strip(), True
    except Exception:
        logger.warning(
            "Could not translate question for retrieval; using original text.",
            exc_info=True,
        )
    return user_question, False
