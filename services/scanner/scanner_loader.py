from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_scanner_profile(path: str | Path) -> Dict[str, Any]:
    profile_path = Path(path)
    with profile_path.open('r', encoding='utf-8') as f:
        return json.load(f)
