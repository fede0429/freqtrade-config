import json
from pathlib import Path

class BridgeLoader:
    def __init__(self, overlay_path, decision_cache_path):
        self.overlay_path = Path(overlay_path)
        self.decision_cache_path = Path(decision_cache_path)

    def _safe_read_json(self, path):
        if not path.exists(): return {}
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return {}

    def load_overlay(self): return self._safe_read_json(self.overlay_path)
    def load_decision_cache(self): return self._safe_read_json(self.decision_cache_path)
