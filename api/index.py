# api/index.py
import sys
import os

# Add project root to path so `from app.main import app` resolves correctly
# __file__ is api/index.py → parent is api/ → parent of that is project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # Vercel detects the `app` variable automatically