"""Tracks the active uploaded document for chat (single-document session)."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import config


def _stored_path_for_manifest(stored_path: Path) -> str:
    """Persist paths relative to project root when possible (portable across machines)."""
    try:
        resolved = stored_path.resolve()
        base = config.BASE_DIR.resolve()
        return str(resolved.relative_to(base))
    except ValueError:
        return str(stored_path.resolve())


def _resolve_stored_path(stored: str, document_id: str) -> Path | None:
    """Resolve manifest stored_path; support legacy absolute paths + doc_id fallback."""
    path = Path(stored)
    if not path.is_absolute():
        path = (config.BASE_DIR / path).resolve()
    else:
        path = path.resolve()
    if path.is_file():
        return path
    # Legacy manifest from another clone: PDF may still live under data/<id>.pdf
    fallback = (config.DATA_DIR / f"{document_id}.pdf").resolve()
    if fallback.is_file():
        return fallback
    return None


@dataclass
class ActiveDocument:
    """Metadata for the document currently indexed for Q&A."""

    document_id: str
    stored_path: Path
    original_filename: str


class DocumentState:
    """Thread-safe persistence of which PDF + vector index is active."""

    def __init__(self, manifest_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._manifest_path = manifest_path or config.MANIFEST_PATH
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _read_manifest(self) -> dict[str, Any] | None:
        if not self._manifest_path.exists():
            return None
        try:
            return json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def get_active(self) -> ActiveDocument | None:
        with self._lock:
            data = self._read_manifest()
            if not data:
                return None
            doc_id = data.get("active_document_id")
            stored = data.get("stored_path")
            name = data.get("original_filename", "document.pdf")
            if not doc_id or not stored:
                return None
            path = _resolve_stored_path(str(stored), doc_id)
            if path is None:
                return None
            return ActiveDocument(
                document_id=doc_id,
                stored_path=path,
                original_filename=name,
            )

    def set_active(
        self,
        stored_path: Path,
        original_filename: str,
        document_id: str | None = None,
    ) -> ActiveDocument:
        doc_id = document_id or str(uuid.uuid4())
        payload = {
            "active_document_id": doc_id,
            "stored_path": _stored_path_for_manifest(stored_path),
            "original_filename": original_filename,
        }
        with self._lock:
            self._manifest_path.write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        return ActiveDocument(
            document_id=doc_id,
            stored_path=stored_path.resolve(),
            original_filename=original_filename,
        )


document_state = DocumentState()
