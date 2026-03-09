from __future__ import annotations

import sys
from pathlib import Path


def get_repo_root(from_file: str | Path | None = None) -> Path:
    if from_file is None:
        return Path(__file__).resolve().parents[2]
    return Path(from_file).resolve().parents[2]


def ensure_repo_on_syspath(from_file: str | Path | None = None) -> Path:
    root = get_repo_root(from_file)
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root
