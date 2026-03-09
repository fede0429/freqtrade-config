from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReleaseDecision:
    approved: bool
    mode: str
    environment: str
    market_type: str
    release_channel: str
    checks: list[CheckResult] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "mode": self.mode,
            "environment": self.environment,
            "market_type": self.market_type,
            "release_channel": self.release_channel,
            "checks": [c.to_dict() for c in self.checks],
            "required_actions": self.required_actions,
        }
