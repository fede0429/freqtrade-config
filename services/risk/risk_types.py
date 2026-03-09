from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PortfolioState:
    equity: float
    available_cash: float
    total_exposure: float
    strategy_exposure: float
    symbol_exposure: float
    correlated_bucket_exposure: float
    open_positions: int
    daily_pnl_ratio: float
    weekly_pnl_ratio: float
    drawdown_ratio: float
    consecutive_losses: int


@dataclass
class MarketState:
    regime: str = "neutral"
    realized_volatility_ratio: float = 0.0
    funding_rate: float = 0.0
    scanner_approved: bool = True
    broad_market_drop_ratio: float = 0.0


@dataclass
class TradeIntent:
    market: str
    strategy: str
    symbol: str
    side: str = "long"
    order_value: float = 0.0
    has_stoploss: bool = True
    proposed_slippage_ratio: float = 0.0
    additional_entry_index: int = 0


@dataclass
class RiskDecision:
    allow: bool
    mode: str
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    cooldown_minutes: Optional[int] = None
