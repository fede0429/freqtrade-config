from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class ProviderHealth:
    provider: str
    kind: str
    status: str
    ts: str
    detail: Optional[str] = None

@dataclass
class ProviderSnapshot:
    provider: str
    kind: str
    pair: str
    status: str
    ts: str
    latency_ms: int
    stale: bool
    score: float
    signals: Dict[str, Any] = field(default_factory=dict)
    risk_flags: List[str] = field(default_factory=list)
    raw_ref: Dict[str, Any] = field(default_factory=dict)
