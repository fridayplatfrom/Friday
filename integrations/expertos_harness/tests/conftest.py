"""Keep the bridge importable when tests are discovered from the parent repo."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
