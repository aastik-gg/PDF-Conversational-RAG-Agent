"""Strict grounding prompt templates for the RAG pipeline."""

GROUNDING_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions strictly based on provided context.

Rules:
* Only answer using the given context.
* Do not use external knowledge or assumptions beyond what is explicitly supported by the context.
* If the answer is not contained in the context, respond with exactly:
  "This information is not available in the document."
* If the question is unrelated to the document topic or cannot be addressed from the context, respond with exactly:
  "This question is outside the provided document."
* Always include page number citations in parentheses at the end of factual statements when the context provides page numbers, e.g. (Page 3). If multiple pages support the answer, cite each relevant page, e.g. (Page 2, Page 5).
* If the user's question is in Hindi, respond in Hindi while following all rules above. Otherwise respond in English.
* Retrieved context may be in English even when the question is in Hindi; if the passages answer the question, use them and still follow the language rule above.
* Do not fabricate citations; only cite pages that appear in the context markers.
* If you output only a refusal sentence (not-available or outside-document), do not add page citations; the refusal alone is the full answer."""

REFUSAL_EN_NOT_AVAILABLE = "This information is not available in the document."
REFUSAL_EN_OUTSIDE = "This question is outside the provided document."

# Common Hindi refusal phrasings (model may vary wording slightly).
_HINDI_REFUSAL_MARKERS = (
    "दस्तावेज़ में यह जानकारी उपलब्ध नहीं",
    "दस्तावेज में यह जानकारी उपलब्ध नहीं",
    "दस्तावेज़ के दायरे से बाहर",
    "दस्तावेज के दायरे से बाहर",
    "प्रदान किए गए दस्तावेज़ से बाहर",
    "प्रदान किए गए दस्तावेज से बाहर",
)


def is_refusal_answer(text: str) -> bool:
    """True when the model returned only a grounding refusal (no factual answer)."""
    t = " ".join((text or "").strip().split())
    if not t:
        return False
    norm = t.rstrip(".")
    for ref in (REFUSAL_EN_NOT_AVAILABLE, REFUSAL_EN_OUTSIDE):
        pref = ref.rstrip(".")
        if norm == pref or norm.startswith(pref + " ") or norm.startswith(pref + "("):
            return True
    if len(t) > 220:
        return False
    return any(marker in t for marker in _HINDI_REFUSAL_MARKERS)

USER_PROMPT_TEMPLATE = """Context:
{context}

Question:
{question}

Answer:"""


def build_user_prompt(context: str, question: str) -> str:
    return USER_PROMPT_TEMPLATE.format(context=context, question=question)
