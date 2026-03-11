from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

class ShadowAuditWriter:
    def __init__(self, base_dir: str = "user_data/agent_runtime/audit"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def append_event(self, filename: str, row: dict[str, Any]) -> None:
        path = self.base_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": self._utc_now(), **row}, ensure_ascii=False) + "\n")
