# Vercel frontend (static)

Build injects your **Render API URL** into `public/index.html`.

**There is no runtime “frontend env” for the API URL.** The static page is just HTML/JS; `API_BASE_URL` is read **only when Node runs `build.mjs`** (your machine or Vercel’s build). Whatever you last built is what you see in `public/index.html` (that file is gitignored; do not hand-edit it for deploys).

## Vercel project settings

1. **Root Directory:** `frontend` (in the Vercel dashboard: Project → Settings → General).
2. **Environment variable (Production & Preview):**
   - `API_BASE_URL` = `https://YOUR-SERVICE.onrender.com` (no trailing slash; use your real Render URL).

3. Deploy (Git integration or `vercel` CLI from repo root with `--cwd frontend`).

## Local preview

```bash
cd frontend
API_BASE_URL=https://your-render-url.onrender.com npm run build
npx serve public
```
