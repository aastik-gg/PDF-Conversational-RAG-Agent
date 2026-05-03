"""Local HuggingFace sentence-transformers embeddings and FAISS persistence."""

from __future__ import annotations

import logging
import shutil
import threading
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app import config

logger = logging.getLogger(__name__)

_embeddings_lock = threading.Lock()
_embeddings: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy singleton: loads the SentenceTransformer model once per process."""
    global _embeddings
    with _embeddings_lock:
        if _embeddings is None:
            model_kwargs: dict = {}
            if config.EMBEDDING_DEVICE:
                model_kwargs["device"] = config.EMBEDDING_DEVICE
            _embeddings = HuggingFaceEmbeddings(
                model_name=config.HF_EMBEDDING_MODEL,
                model_kwargs=model_kwargs,
                encode_kwargs={
                    "normalize_embeddings": True,
                    "batch_size": config.EMBEDDING_ENCODE_BATCH,
                },
            )
            logger.info("Loaded local embedding model: %s", config.HF_EMBEDDING_MODEL)
        return _embeddings


def vectorstore_path_for(document_id: str) -> Path:
    return config.VECTOR_DIR / document_id


def build_and_save_faiss(documents: list[Document], document_id: str) -> Path:
    """Create a FAISS index from chunked documents and persist it to disk."""
    embeddings = get_embeddings()
    out = vectorstore_path_for(document_id)
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = len(documents)
    batch = max(1, config.FAISS_INDEX_BATCH_SIZE)
    logger.info(
        "Building FAISS index with %d chunks (batch_size=%d, encode_batch=%d)",
        n,
        batch,
        config.EMBEDDING_ENCODE_BATCH,
    )
    if n == 0:
        raise ValueError("No documents to index.")
    store = FAISS.from_documents(documents[:batch], embeddings)
    for start in range(batch, n, batch):
        end = min(start + batch, n)
        store.add_documents(documents[start:end])
        logger.info("Indexed chunks %d–%d of %d", start, end - 1, n)
    store.save_local(str(out))
    logger.info("Saved FAISS index to %s", out)
    return out


def load_faiss(document_id: str) -> FAISS:
    """Load a persisted FAISS store; requires the same embedding model as at index time."""
    path = vectorstore_path_for(document_id)
    if not path.exists():
        raise FileNotFoundError(f"No vector index found for document id {document_id}.")
    embeddings = get_embeddings()
    return FAISS.load_local(
        str(path),
        embeddings,
        allow_dangerous_deserialization=True,
    )
