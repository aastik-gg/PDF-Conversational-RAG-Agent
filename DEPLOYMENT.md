# Deployment guide

## Recommended split: **Render (API)** + **Vercel (UI)** — no Docker

Your backend is **FastAPI + local ML + disk**; Render’s **native Python Web Service** can run it (ephemeral disk, cold starts on free tier). The UI is a **static site** built with a tiny Node script that injects your Render URL.

---

### Part A — Backend on Render (native Python)

1. **Push this repo** to GitHub (or GitLab / Bitbucket).

2. In [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint** (or **Web Service**).

   **Blueprint:** connect the repo; Render reads **`render.yaml`** at the root.

   **Web Service (manual):**
   - **Runtime:** Python 3
   - **Root directory:** leave empty (repo root)
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free is OK for demos (service **spins down** when idle; first request is slow).

3. **Environment variables** (Render → your service → **Environment**):

   | Key | Value |
   |-----|--------|
   | `GOOGLE_API_KEY` | Your Gemini / Google AI API key |
   | `GEMINI_MODEL` | e.g. `gemini-2.0-flash` |
   | `PYTHON_VERSION` | `3.12.8` (matches `.python-version`) |
   | `CORS_ORIGINS` | Your Vercel origin(s), comma-separated, **no** `*` in production. Example: `https://pdf-agent-ui.vercel.app` |

   Optional: `HF_EMBEDDING_MODEL`, `EMBEDDING_DEVICE` (see `app/config.py`).

4. **Deploy** and wait for the build (first build downloads PyTorch / sentence-transformers — **10–20+ minutes** on free tier is common).

5. Copy the service URL, e.g. `https://pdf-conversational-agent-xxxx.onrender.com`.

6. **Smoke test:** `curl https://YOUR-SERVICE.onrender.com/health` → `{"status":"ok"}`.

**Notes**

- **Disk is ephemeral** on Render: uploads and FAISS survive until the instance is recycled. For a serious demo, re-upload after long idle or use a paid instance / external storage later.
- **PDF size:** Render HTTP limits are much higher than Vercel’s; large PDFs are OK relative to serverless.
- **`CORS_ORIGINS`:** Must include your exact Vercel URL (`https://…vercel.app`). Until set, you can temporarily use `*` for debugging only (credentials off).

---

### Part B — Frontend on Vercel (static + build)

The **`frontend/`** folder is a minimal Vercel project: **`npm run build`** runs **`build.mjs`**, which reads **`API_BASE_URL`** and writes **`public/index.html`** from **`template.html`**.

1. **Create a Vercel project** from the **same** Git repo.

2. **Settings → General → Root Directory:** set to **`frontend`**.

3. **Settings → Environment Variables** (Production and Preview):

   | Name | Value |
   |------|--------|
   | `API_BASE_URL` | `https://YOUR-SERVICE.onrender.com` (no trailing slash) |

4. **Deploy.** Vercel runs `npm install` (no deps) + `npm run build` → outputs **`public/`**.

5. Open your **`*.vercel.app`** site; upload a PDF and chat. If the browser shows CORS errors, fix **`CORS_ORIGINS`** on Render to match this exact Vercel URL (scheme + host, no path).

6. **Local check** (optional):

   ```bash
   cd frontend
   API_BASE_URL=https://your-service.onrender.com npm run build
   npx --yes serve public
   ```

---

### Order of operations

1. Deploy **Render** first → get `https://….onrender.com`.
2. Set Render **`CORS_ORIGINS`** to your future Vercel URL (you can redeploy Render after Vercel gives you the hostname, or use a custom domain).
3. Deploy **Vercel** with **`API_BASE_URL`** pointing at Render.

---

## Optional: FastAPI on Vercel (not recommended for this repo)

See the bottom of the previous version: body size, ephemeral disk, and huge ML bundles make **full** hosting on Vercel painful. **`api/index.py`** + **`vercel.json`** remain for experiments only; prefer Render for the API.

---

## Files reference

| File | Role |
|------|------|
| `render.yaml` | Render Blueprint (Python web service, no Docker) |
| `.python-version` | Python version hint for Render |
| `frontend/` | Vercel static UI + `build.mjs` injects `API_BASE_URL` |
| `app/main.py` | `CORS_ORIGINS` env for browser → Render API |
