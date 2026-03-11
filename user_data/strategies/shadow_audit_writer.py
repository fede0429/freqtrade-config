from __future__ import annotations
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = REPO_ROOT / "user_data/agent_runtime/state"
CURRENT_RUN_ID_FILE = STATE_DIR / "current_run_id.txt"
RUN_ID_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


class ShadowAuditWriter:
    def __init__(self, base_dir: str = "user_data/agent_runtime/audit"):
        base_path = Path(base_dir)
        self.trace_root = base_path if base_path.is_absolute() else REPO_ROOT / base_path
        self.trace_root.mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.run_id = self._resolve_run_id()
        CURRENT_RUN_ID_FILE.write_text(self.run_id + "\n", encoding="utf-8")
        self.base_dir = self.trace_root / self.run_id
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _default_run_id(self) -> str:
        return datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")

    def _sanitize_run_id(self, value: str) -> str:
        cleaned = RUN_ID_PATTERN.sub("-", value).strip("-._")
        return cleaned or self._default_run_id()

    def _resolve_run_id(self) -> str:
        env_value = os.environ.get("AGENT_RUN_ID", "").strip()
        if env_value:
            return self._sanitize_run_id(env_value)
        if CURRENT_RUN_ID_FILE.exists():
            file_value = CURRENT_RUN_ID_FILE.read_text(encoding="utf-8-sig").strip()
            if file_value:
                return self._sanitize_run_id(file_value)
        return self._default_run_id()

    def append_event(self, filename: str, row: dict[str, Any]) -> None:
        path = self.base_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(row)
        event_time = payload.pop("event_time", None)
        written_at = self._utc_now()
        record = {
            "ts": event_time or written_at,
            "written_at": written_at,
            "run_id": self.run_id,
            **payload,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
