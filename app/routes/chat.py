"""Upload and chat endpoints."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from app import config
from app.document_state import document_state
from app.services import embeddings as embeddings_service
from app.services import llm as llm_service
from app.services import pdf_loader
from app.services.query_adapter import prepare_retrieval_query
from app.services.retriever import build_context_string, retrieve_for_question
from app.utils.prompts import is_refusal_answer

logger = logging.getLogger("pdf_agent.chat")

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Question cannot be empty or whitespace only.")
        return stripped


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict] = Field(
        default_factory=list,
        description="Pages referenced by retrieved chunks (not a second LLM pass).",
    )


class UploadResponse(BaseModel):
    document_id: str
    message: str
    chunks: int
    filename: str


def _extract_citations_from_chunks(retrieved) -> list[dict]:
    cites: list[dict] = []
    seen: set[int] = set()
    for doc in retrieved:
        page = doc.metadata.get("page_number")
        if isinstance(page, int) and page not in seen:
            seen.add(page)
            cites.append({"page": page})
    return cites


def _sanitize_detail(exc: Exception) -> str:
    msg = str(exc).strip()
    if len(msg) > 240:
        msg = msg[:237] + "..."
    return msg


def _embed_pdf_at_path(pdf_path: Path, document_id: str) -> int:
    """Chunk + embed + save FAISS for an existing PDF path; returns chunk count."""
    chunks = pdf_loader.ingest_pdf(pdf_path)
    embeddings_service.build_and_save_faiss(chunks, document_id)
    return len(chunks)


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    """Accept a PDF, persist it, chunk, embed, and build a FAISS index."""
    filename = file.filename or "upload.pdf"
    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = str(uuid.uuid4())
    dest = config.DATA_DIR / f"{doc_id}.pdf"
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        dest.write_bytes(raw)
    except HTTPException:
        raise
    except OSError as exc:
        logger.exception("Failed to save upload")
        raise HTTPException(status_code=500, detail=_sanitize_detail(exc)) from exc

    try:
        chunk_count = _embed_pdf_at_path(dest, doc_id)
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        logger.warning("PDF ingestion failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        dest.unlink(missing_ok=True)
        logger.exception("Unexpected error during PDF ingestion")
        raise HTTPException(
            status_code=502,
            detail="Embedding or indexing failed. Check logs; first run may download the HuggingFace model.",
        ) from exc

    document_state.set_active(dest, filename, document_id=doc_id)
    logger.info("Upload complete document_id=%s chunks=%d", doc_id, chunk_count)
    return UploadResponse(
        document_id=doc_id,
        message="PDF processed and ready for questions.",
        chunks=chunk_count,
        filename=filename,
    )


@router.post("/reindex", response_model=UploadResponse)
def reindex_active_pdf() -> UploadResponse:
    """
    Rebuild the FAISS index for the active document from the PDF on disk.

    Use this after changing the embedding model (or migrating from another
    embedder). Old vectors cannot be converted — chunks must be re-embedded.
    """
    active = document_state.get_active()
    if not active:
        raise HTTPException(
            status_code=400,
            detail="No active document. Upload a PDF first via POST /upload.",
        )
    try:
        chunk_count = _embed_pdf_at_path(active.stored_path, active.document_id)
    except ValueError as exc:
        logger.warning("Reindex failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Reindex failed")
        raise HTTPException(
            status_code=502,
            detail="Reindex failed. Check logs and embedding model setup.",
        ) from exc

    logger.info(
        "Reindex complete document_id=%s chunks=%d", active.document_id, chunk_count
    )
    return UploadResponse(
        document_id=active.document_id,
        message="FAISS index rebuilt with the current embedding model.",
        chunks=chunk_count,
        filename=active.original_filename,
    )


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Answer a question using only the active PDF context (strict grounding)."""
    active = document_state.get_active()
    if not active:
        raise HTTPException(
            status_code=400,
            detail="No document is loaded. Upload a PDF first via POST /upload.",
        )

    question = req.question
    logger.info("User query: %s", question)

    retrieval_question, _used_translation = prepare_retrieval_query(question)

    try:
        retrieved = retrieve_for_question(active.document_id, retrieval_question)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Retrieval failed")
        raise HTTPException(
            status_code=502,
            detail="Retrieval failed. Check the embedding model and FAISS index.",
        ) from exc

    if not retrieved:
        logger.warning("No chunks retrieved for query")
        raise HTTPException(
            status_code=422,
            detail="No relevant passages could be retrieved from the document.",
        )

    context = build_context_string(retrieved)
    logger.info("Retrieved context:\n%s", context)

    try:
        answer = llm_service.generate_grounded_answer(context=context, question=question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("LLM invocation failed")
        raise HTTPException(
            status_code=502,
            detail="The language model request failed. Check GOOGLE_API_KEY and model name.",
        ) from exc

    citations = _extract_citations_from_chunks(retrieved)
    if is_refusal_answer(answer):
        # Retrieval always returns top-k chunks; those pages are not "supporting"
        # a refusal-only answer, so omit citations to avoid confusing users.
        citations = []
    logger.info("Final response: %s", answer)
    return ChatResponse(answer=answer, citations=citations)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
