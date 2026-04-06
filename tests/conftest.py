import sys
from pathlib import Path

# Allow imports from project root (scraper, exporter, config) without installation.
sys.path.insert(0, str(Path(__file__).parent.parent))
