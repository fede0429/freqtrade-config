from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromotionInput:
    strategy_name: str
    backtest_days: int
    max_drawdown: float
    profit_factor: float
    win_rate: float
    dry_run_days: int
    canary_days: int


@dataclass(frozen=True)
class PromotionDecision:
    allow_upgrade: bool
    reasons: list[str]


class PromotionPolicy:
    def __init__(self, upgrade_gate: dict) -> None:
        self.gate = upgrade_gate

    def evaluate(self, candidate: PromotionInput) -> PromotionDecision:
        reasons: list[str] = []

        if candidate.backtest_days < self.gate["required_backtest_days"]:
            reasons.append("insufficient_backtest_window")
        if candidate.max_drawdown > self.gate["max_backtest_drawdown"]:
            reasons.append("drawdown_above_limit")
        if candidate.profit_factor < self.gate["min_profit_factor"]:
            reasons.append("profit_factor_below_gate")
        if candidate.win_rate < self.gate["min_win_rate"]:
            reasons.append("win_rate_below_gate")
        if candidate.dry_run_days < self.gate["dry_run_days"]:
            reasons.append("insufficient_dry_run_days")
        if candidate.canary_days < self.gate["canary_days"]:
            reasons.append("insufficient_canary_days")

        return PromotionDecision(allow_upgrade=not reasons, reasons=reasons)
