from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class BridgeLoader:
    def __init__(self, overlay_path: str, decision_cache_path: str):
        self.overlay_path = Path(overlay_path)
        self.decision_cache_path = Path(decision_cache_path)

    def _safe_read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def load_overlay(self) -> dict[str, Any]:
        return self._safe_read_json(self.overlay_path)

    def load_decision_cache(self) -> dict[str, Any]:
        return self._safe_read_json(self.decision_cache_path)

    def pair_decision(self, pair: str) -> dict[str, Any]:
        cache = self.load_decision_cache()
        return cache.get("pairs", {}).get(pair.upper(), {})
