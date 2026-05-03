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
HF_EMBEDDING_MODEL = os.getenv(
    "HF_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
# Optional: "cpu", "cuda", "cuda:0", etc. Empty = sentence-transformers default
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "").strip()

# RAG
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))
CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "800"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "100"))
