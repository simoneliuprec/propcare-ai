import sys
from pathlib import Path

# Add /backend to sys.path so "import app" works in tests
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
