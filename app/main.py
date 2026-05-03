"""FastAPI entry point for the PDF conversational agent."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.document_state import document_state
from app.routes import chat

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


configure_logging()
logger = logging.getLogger("pdf_agent")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _cors_settings() -> tuple[list[str], bool]:
    """
    CORS_ORIGINS: comma-separated list, e.g.
    https://your-app.vercel.app,https://www.yourdomain.com
    Use * for local dev only (credentials disabled — browser rules).
    """
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"], False
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins, True


_cors_origins, _cors_credentials = _cors_settings()

app = FastAPI(
    title="PDF Conversational Agent",
    description="Strictly grounded Q&A over uploaded PDFs (English / Hindi).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_model=None)
def serve_ui():
    """Serve the optional minimal HTML UI when present."""
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return HTMLResponse(
            content=(
                "<h1>PDF Conversational Agent</h1>"
                "<p>API is running. Add <code>static/index.html</code> for the UI, "
                "or call <code>POST /upload</code> and <code>POST /chat</code>.</p>"
            ),
            status_code=200,
        )
    return FileResponse(index, media_type="text/html")


@app.on_event("startup")
async def startup_event() -> None:
    active = document_state.get_active()
    if active:
        logger.info("Active document on startup: %s", active.document_id)
    else:
        logger.info("No active document. Awaiting upload.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
