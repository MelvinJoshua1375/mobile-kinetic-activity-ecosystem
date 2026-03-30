"""
Vercel serverless function entry point.
Wraps the FastAPI app so Vercel can serve it as a Python function.
"""

import sys
from pathlib import Path

# Add backend package to sys.path so `app.*` imports resolve
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.main import app  # noqa: E402, F401 — Vercel discovers this
