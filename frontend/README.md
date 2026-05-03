# Vercel frontend (static)

Build injects your **Render API URL** into `public/index.html`.

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
