from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parent
src_path = root / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
