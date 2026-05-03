"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent of app/)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VECTOR_DIR = BASE_DIR / "vectorstore"
MANIFEST_PATH = DATA_DIR / "manifest.json"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Local sentence-transformers (HuggingFace) — no API key required
_DEFAULT_HF_EMBED = "sentence-transformers/all-MiniLM-L6-v2"
# Smaller / lighter checkpoint for ~512MB RAM (Render free, etc.)
_SMALL_HF_EMBED = "sentence-transformers/paraphrase-MiniLM-L3-v2"


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


# Render injects RENDER=true; use tighter memory unless user overrides batches/model.
_LOW_RAM = _truthy("LOW_RAM") or os.getenv("RENDER", "").strip().lower() == "true"

_raw_hf = os.environ.get("HF_EMBEDDING_MODEL")
if _raw_hf is not None and _raw_hf.strip():
    HF_EMBEDDING_MODEL = _raw_hf.strip()
elif _LOW_RAM:
    HF_EMBEDDING_MODEL = _SMALL_HF_EMBED
else:
    HF_EMBEDDING_MODEL = _DEFAULT_HF_EMBED

# Optional: "cpu", "cuda", "cuda:0", etc. Empty = sentence-transformers default
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "").strip() or ("cpu" if _LOW_RAM else "")

# RAG
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))
CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "800"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "100"))

# Low-RAM: tiny encode batches + incremental FAISS (defaults stricter on Render)
_EMBED_BATCH_DEFAULT = "2" if _LOW_RAM else "8"
_FAISS_BATCH_DEFAULT = "4" if _LOW_RAM else "16"
EMBEDDING_ENCODE_BATCH = int(os.getenv("EMBEDDING_ENCODE_BATCH", _EMBED_BATCH_DEFAULT))
FAISS_INDEX_BATCH_SIZE = int(os.getenv("FAISS_INDEX_BATCH_SIZE", _FAISS_BATCH_DEFAULT))

LOW_RAM = _LOW_RAM
