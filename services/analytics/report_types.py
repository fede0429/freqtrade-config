from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ReportSummary:
    date: str
    market_type: str
    profile_name: str
    equity_start: float
    equity_end: float
    realized_pnl: float
    unrealized_pnl: float
    net_pnl: float
    return_pct: float
    fees: float
    open_positions: int
    closed_trades: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyHealth:
    name: str
    stage: str
    market: str
    risk_budget_fraction: float
    exposure_usd: float
    realized_pnl: float
    open_positions: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationsReport:
    generated_at: str
    summary: ReportSummary
    scanner: dict[str, Any]
    risk: dict[str, Any]
    data_sources: dict[str, Any]
    strategies: list[StrategyHealth]
    top_winners: list[dict[str, Any]]
    top_losers: list[dict[str, Any]]
    risk_events: list[dict[str, Any]]
    execution_funnel: dict[str, Any]
    missed_alpha: dict[str, Any]
    decision_to_fill: dict[str, Any]
    outcome_comparison: dict[str, Any]
    replace_cost_analysis: dict[str, Any]
    integrity_checks: dict[str, Any]
    traceability: dict[str, Any]
    alert_summary: dict[str, Any]
    health_pack: dict[str, Any]
    narrative: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            'generated_at': self.generated_at,
            'summary': self.summary.to_dict(),
            'scanner': self.scanner,
            'risk': self.risk,
            'data_sources': self.data_sources,
            'strategies': [item.to_dict() for item in self.strategies],
            'top_winners': self.top_winners,
            'top_losers': self.top_losers,
            'risk_events': self.risk_events,
            'execution_funnel': self.execution_funnel,
            'missed_alpha': self.missed_alpha,
            'decision_to_fill': self.decision_to_fill,
            'outcome_comparison': self.outcome_comparison,
            'replace_cost_analysis': self.replace_cost_analysis,
            'integrity_checks': self.integrity_checks,
            'traceability': self.traceability,
            'alert_summary': self.alert_summary,
            'health_pack': self.health_pack,
            'narrative': self.narrative,
        }
