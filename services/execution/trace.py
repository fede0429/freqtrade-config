from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class TraceContext:
    run_id: str
    trace_id: str
    parent_trace_id: str | None
    stage: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_run_id(prefix: str) -> str:
    seed = f'{prefix}:{utc_now_iso()}'
    return f'{prefix}:{hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]}'


def build_trace_context(*, stage: str, run_id: str, parent_trace_id: str | None = None, seed: str | None = None) -> TraceContext:
    body = f'{run_id}:{stage}:{parent_trace_id or "root"}:{seed or utc_now_iso()}'
    trace_id = hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]
    return TraceContext(run_id=run_id, trace_id=trace_id, parent_trace_id=parent_trace_id, stage=stage, created_at=utc_now_iso())
