import json
from pathlib import Path
from datetime import datetime, timezone

class ShadowAuditWriter:
    def __init__(self, base_dir="user_data/agent_runtime/audit"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _utc_now(self):
        return datetime.now(timezone.utc).isoformat()

    def append_event(self, filename, row):
        p = self.base_dir / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": self._utc_now(), **row}, ensure_ascii=False) + "\n")
