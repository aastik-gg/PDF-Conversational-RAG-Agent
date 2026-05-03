"""Retrieve top-k chunks from FAISS for a question."""

from __future__ import annotations

import logging

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app import config
from app.services.embeddings import load_faiss

logger = logging.getLogger(__name__)


def format_context_block(doc: Document, index: int) -> str:
    page = doc.metadata.get("page_number")
    header = f"[Segment {index + 1}"
    if page is not None:
        header += f", Page {page}"
    header += "]"
    body = (doc.page_content or "").strip()
    return f"{header}\n{body}"


def build_context_string(docs: list[Document]) -> str:
    parts = [format_context_block(d, i) for i, d in enumerate(docs)]
    return "\n\n".join(parts)


def retrieve_for_question(document_id: str, question: str, k: int | None = None) -> list[Document]:
    """Similarity search over the FAISS index for this document."""
    k = k or config.RETRIEVAL_K
    store: FAISS = load_faiss(document_id)
    docs = store.similarity_search(question, k=k)
    logger.info("Retrieved %d chunks for query", len(docs))
    return docs
