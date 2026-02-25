# api/index.py
# Vercel entry point — adds project root to path and exports the FastAPI app.
import sys
import os

# Walk up from api/ to project root
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)

from app.main import app  # Vercel detects `app` automatically