from __future__ import annotations
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


class BridgeLoader:
    def __init__(self, overlay_path: str, decision_cache_path: str):
        self.overlay_path = self._resolve_path(overlay_path)
        self.decision_cache_path = self._resolve_path(decision_cache_path)

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else REPO_ROOT / path

    def _safe_read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def load_overlay(self) -> dict[str, Any]:
        return self._safe_read_json(self.overlay_path)

    def load_decision_cache(self) -> dict[str, Any]:
        return self._safe_read_json(self.decision_cache_path)
