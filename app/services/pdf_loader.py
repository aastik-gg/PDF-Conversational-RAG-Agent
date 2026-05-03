"""Load PDFs with LangChain PyPDFLoader and chunk with token-aware splitting."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from app import config

if TYPE_CHECKING:
    from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def _page_display_number(metadata: dict) -> int | None:
    raw = metadata.get("page")
    if raw is None:
        return None
    try:
        return int(raw) + 1
    except (TypeError, ValueError):
        return None


def load_pdf_documents(pdf_path: Path) -> list[Document]:
    """Load all pages from a PDF as LangChain documents with page metadata."""
    from langchain_community.document_loaders import PyPDFLoader

    loader = PyPDFLoader(str(pdf_path))
    docs = loader.load()
    if not docs:
        raise ValueError("The PDF contains no pages.")
    for d in docs:
        page = _page_display_number(d.metadata)
        if page is not None:
            d.metadata["page_number"] = page
    return docs


def chunk_documents(documents: list[Document]) -> list[Document]:
    """Split documents into overlapping chunks; preserve page_number in metadata."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=config.CHUNK_SIZE_TOKENS,
        chunk_overlap=config.CHUNK_OVERLAP_TOKENS,
        add_start_index=False,
    )
    chunks = splitter.split_documents(documents)
    for c in chunks:
        if "page_number" not in c.metadata:
            page = _page_display_number(c.metadata)
            if page is not None:
                c.metadata["page_number"] = page
    return chunks


def validate_non_empty_text(documents: list[Document]) -> None:
    """Raise if the PDF has no extractable text (empty or scanned-only)."""
    total = sum(len((d.page_content or "").strip()) for d in documents)
    if total == 0:
        raise ValueError(
            "No extractable text was found in the PDF. "
            "It may be empty, image-only, or protected."
        )


def ingest_pdf(pdf_path: Path) -> list[Document]:
    """End-to-end: load PDF, validate text, chunk for embedding."""
    logger.info("Loading PDF: %s", pdf_path)
    documents = load_pdf_documents(pdf_path)
    validate_non_empty_text(documents)
    chunks = chunk_documents(documents)
    if not chunks:
        raise ValueError("Chunking produced no segments from the PDF.")
    non_empty_chunks = [c for c in chunks if (c.page_content or "").strip()]
    if not non_empty_chunks:
        raise ValueError("All text chunks are empty after processing.")
    logger.info("Created %d chunks from PDF", len(non_empty_chunks))
    return non_empty_chunks
