from __future__ import annotations

from abc import ABC, abstractmethod
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


class SkillProvider(ABC):
    name: str = "base_provider"
    kind: str = "generic"

    @abstractmethod
    def health(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    def supports_pair(self, pair: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch(self, pair: str, context: Optional[Dict[str, Any]] = None) -> ProviderSnapshot:
        raise NotImplementedError


class MarketDataProvider(SkillProvider, ABC):
    kind: str = "market_data"

    @abstractmethod
    def fetch_technical_snapshot(
        self, pair: str, timeframe: str, context: Optional[Dict[str, Any]] = None
    ) -> ProviderSnapshot:
        raise NotImplementedError


class OnchainLiquidityProvider(SkillProvider, ABC):
    kind: str = "onchain_liquidity"

    @abstractmethod
    def fetch_liquidity_snapshot(
        self, pair: str, context: Optional[Dict[str, Any]] = None
    ) -> ProviderSnapshot:
        raise NotImplementedError
