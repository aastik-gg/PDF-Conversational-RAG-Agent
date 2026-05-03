"""
Vercel Python Functions entry for FastAPI.

See https://vercel.com/docs/frameworks/backend/fastapi — Vercel expects a
``FastAPI`` instance named ``app`` in supported paths such as ``api/index.py``.

Deploying the *full* PDF agent on Vercel is still limited by body size, disk,
and ML bundle size; read ``DEPLOYMENT.md`` before relying on this in production.
"""

from app.main import app

__all__ = ["app"]
