from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class ScanDecision:
    pair: str
    decision: str
    score: float
    reasons: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarketRegime:
    regime: str
    confidence: float
    breadth: float
    market_pressure: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PairRanking:
    pair: str
    score: float
    momentum_24h: float
    momentum_1h: float
    volume_ratio: float
    volatility: float
    liquidity_usd: float
    tradable: bool
    risk_flags: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScanSnapshot:
    scan_timestamp: str
    profile_name: str
    market: str
    tradable_pairs: List[str]
    market_regime: MarketRegime
    risk_flags: List[str]
    ranking_scores: List[PairRanking]
    pair_decisions: List[ScanDecision]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload['market_regime'] = self.market_regime.to_dict()
        payload['ranking_scores'] = [item.to_dict() for item in self.ranking_scores]
        payload['pair_decisions'] = [item.to_dict() for item in self.pair_decisions]
        return payload
