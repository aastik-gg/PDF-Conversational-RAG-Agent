# Deployment guide (including Vercel)

This app is a **stateful FastAPI** service with **local ML** (`sentence-transformers` / PyTorch), **disk-backed** PDFs + **FAISS**, and **multi‑MB uploads**. That shape conflicts with typical **Vercel Serverless** constraints unless you **split** the stack or **redesign** storage and ML.

Read this before spending time on a Vercel-only deploy.

---

## Hard limits on Vercel Serverless (why the full app usually fails there)

| Constraint | Impact on this project |
|------------|-------------------------|
| **~4.5 MB** max request/response body | Many **PDF uploads** exceed this → `413` on `POST /upload`. |
| **Ephemeral filesystem** | `data/`, `vectorstore/`, and HF **model cache** are not a durable VM disk; **cold starts** lose local state unless you use external storage + DB. |
| **Large Python bundle** | **PyTorch + `sentence-transformers`** is hundreds of MB; builds are **slow**, may hit **size** limits, and **cold starts** are painful. |
| **Duration / memory** | First embedding load + PDF ingest can exceed **hobby** timeouts unless tuned and upgraded. |

So: **Vercel is a poor primary host for the current architecture.** Use it for **static UI** or move the API to a **container/VM** platform.

---

## Recommended: API on Railway / Render / Fly / Cloud Run + optional Vercel UI

### 1) Deploy the API (pick one provider)

General pattern:

1. **Dockerfile** (recommended) or provider “Python” build with `requirements.txt`.
2. Set env: `GOOGLE_API_KEY`, `GEMINI_MODEL`, optional `HF_EMBEDDING_MODEL`, `EMBEDDING_DEVICE`.
3. Attach a **persistent volume** (or managed object storage later) for `data/` and `vectorstore/` if you need indexes to survive restarts.
4. Expose **HTTPS** on port **8000** (or whatever `CMD` uses).
5. **CORS**: your FastAPI app already allows `*`; for production, restrict to your frontend origin(s).

Example **Docker** run command:

```dockerfile
# Minimal sketch — adjust for your provider
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Then point your browser or Postman at the provider URL.

### 2) (Optional) Put only the HTML UI on Vercel

1. Copy `static/index.html` → **`public/index.html`** in a small Vercel project (or the same repo with “Other” / static output).
2. Change the `fetch("/upload")` and `fetch("/chat")` calls to use your **API base URL**, e.g.  
   `const API_BASE = "https://your-api.railway.app";`  
   then `fetch(\`${API_BASE}/upload\`, …)`.
3. Deploy on Vercel; set **no** sensitive keys in the static file (only the public API URL).

Evaluators still hit the **same** backend; the UI is just hosted on Vercel’s CDN.

---

## If you still want the FastAPI app on Vercel (experimental)

Official docs: [Deploy a FastAPI app on Vercel](https://vercel.com/docs/frameworks/backend/fastapi).

This repo includes **`api/index.py`** that re-exports the FastAPI instance as `app` (required name). **`vercel.json`** excludes dev artifacts and local indexes from the upload bundle.

**Steps:**

1. Install [Vercel CLI](https://vercel.com/docs/cli) (`npm i -g vercel`) and log in.
2. From the **repository root** (where `requirements.txt` lives):  
   `vercel`  
   Link the project; choose **Python** / detected FastAPI when prompted (CLI ≥ **48.1.8** per Vercel).
3. In the Vercel dashboard, add **Environment Variables**: `GOOGLE_API_KEY`, `GEMINI_MODEL`, etc. (same as `.env`).
4. Redeploy after changing env.
5. **Test** `GET /health` on the assigned `*.vercel.app` URL.

**You must accept:**

- **Small PDFs only** (under the body limit) or change the product to **upload to S3** + process asynchronously.
- **Cold starts** and possible **OOM** during first model load.
- **No guarantee** of persistent `data/` / `vectorstore/` across invocations without redesign.

---

## Summary

| Goal | Where to deploy |
|------|-----------------|
| **Production-like** full stack | **Railway, Render, Fly.io, Cloud Run, ECS**, etc. |
| **Vercel** | **Static UI** + API elsewhere, **or** experimental **full FastAPI** with the limits above |

For evaluator handoff, prefer **`EVALUATORS.md`** + a **stable API URL** on a container host rather than fighting Vercel limits for this codebase.
