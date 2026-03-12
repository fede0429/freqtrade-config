from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class RawNewsItem:
    source_name: str
    source_type: str
    category: str
    title: str
    body: str
    url: str
    published_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NormalizedEvent:
    event_id: str
    source_name: str
    source_tier: str
    event_type: str
    headline: str
    summary: str
    sentiment_score: float
    credibility_score: float
    impact_horizon: str
    affected_assets: List[str]
    market_regime_bias: str
    risk_flags: List[str]
    review_required: bool
    published_at: str
    url: str
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
