# Technical note for evaluators

Short overview of architecture, design choices, trade-offs, and how to run checks.

## Purpose

A **strictly grounded** PDF Q&A service: answers must follow **retrieved** document chunks; **page-level** citations; clear **refusals** for missing or off-topic content; **English and Hindi** user questions (Hindi answers when the question is Hindi).

## Architecture (high level)

1. **Ingest** — `POST /upload` saves the PDF, extracts text with **LangChain `PyPDFLoader`**, splits with **tiktoken-sized** chunks (~800 / ~100 overlap), embeds with **local `sentence-transformers`** (`HuggingFaceEmbeddings`), stores vectors in **FAISS** on disk (`vectorstore/<document_id>/`).
2. **Query** — `POST /chat` embeds the question (same model), **similarity search** (default *k* = 4), formats hits with **page markers**, calls **Gemini** with a **strict system prompt** (no outside knowledge; fixed refusal strings when appropriate).
3. **Session** — One **active** document at a time (`data/manifest.json`, **gitignored**). It stores a **path relative to the project root** (and falls back to `data/<document_id>.pdf` if an old absolute path from another machine is stale). New upload replaces the active index.

```text
PDF → chunk → local embed → FAISS
                              ↑
                    question (→ English for search if Hindi-heavy)
                              ↓
                    top-k chunks + pages → Gemini → answer
```

## Notable decisions

| Decision | Rationale |
|----------|-----------|
| **Local embeddings** | No OpenAI key; predictable cost; runs offline after model download. |
| **Gemini for chat** | Strong instruction following and multilingual generation from a single API key. |
| **Hindi query → English for retrieval only** | English PDFs + English-centric default embedder (`all-MiniLM-L6-v2`) align poorly with Hindi queries; a **small translation step** (same Gemini) improves recall; the **original** Hindi question is still used for the final answer (language match). |
| **Refusal answers → empty `citations`** | Retrieval always returns *k* chunks; listing pages next to a **pure refusal** was misleading—citations are omitted when the answer is detected as refusal-only. |
| **`POST /reindex`** | Rebuild FAISS from the saved PDF after changing `HF_EMBEDDING_MODEL` / device. **Vectors cannot be migrated** across embedding models. |

## Trade-offs (intentional)

- **Single active PDF** — Simple state; not multi-tenant. Production would separate users/sessions and storage.
- **Embedding model** — Default MiniLM is small and fast; **multilingual** or larger models trade RAM/speed for better non-English retrieval without translation.
- **Grounding** — Enforced by **retrieval + prompts**, not a formal verifier; edge cases (borderline relevance) depend on *k* and chunk quality.
- **Scanned PDFs** — No OCR; image-only PDFs may yield “no text” errors.
- **`--api` / live tests** — Need a **running server**, valid **`.env`**, and an **uploaded** fixture PDF; they call real Gemini (cost/latency).

## Paths & deployment

- **`EVALUATORS.md` and `README.md`** use **repo-relative** commands (e.g. `cd` into the folder you cloned—**not** a developer-specific absolute path).
- **`data/manifest.json`** is **local runtime state** (ignored by git). Each evaluator gets a new manifest after `POST /upload`. Do **not** commit machine-specific absolute paths.

## Environment

- **`GOOGLE_API_KEY`**, **`GEMINI_MODEL`** — required for chat (and for Hindi→English retrieval translation).
- **`HF_EMBEDDING_MODEL`**, **`EMBEDDING_DEVICE`** — optional; sensible defaults in `app/config.py`.

## Test instructions for evaluators

### 1) Install and run

```bash
cd <path-to-cloned-repo>   
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
# Set .env (at least GOOGLE_API_KEY, GEMINI_MODEL)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Index the reference PDF

Upload **`tests/fixtures/PM_OneNight_MasterGuide.pdf`** (UI at `/` or `curl -F file=@tests/fixtures/PM_OneNight_MasterGuide.pdf http://127.0.0.1:8000/upload`).

### 3) Automated checks

```bash
pytest tests/test_cases.py -q
# Optional smoke: hits /health + one /chat (needs server + uploaded PDF)
export RUN_LIVE_API_TESTS=1
pytest tests/test_cases.py -q
```

### 4) Full question matrix (answers printed)

With the same server and active PDF:

```bash
python tests/test_cases.py --api
```

Runs all **5 grounded + 3 refusal** catalog questions from `tests/test_cases.py` and prints responses. Optional: `TEST_BASE_URL` if not `http://127.0.0.1:8000`.

### 5) What to look for

- **Grounded** answers cite pages and stay on document content.  
- **Invalid** questions return the documented refusal behavior, **without** spurious citation footers.  
- **Hindi** questions return **Hindi** answers when content exists; English PDF + Hindi is handled via retrieval translation as above.

Further API detail and curl examples: **`README.md`**.
