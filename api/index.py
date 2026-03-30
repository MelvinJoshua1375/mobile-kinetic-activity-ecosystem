"""Vercel serverless function — wraps FastAPI app."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.server import app  # noqa: E402, F401
