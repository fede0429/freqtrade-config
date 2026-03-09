from __future__ import annotations

from typing import Any, Dict, List

from .risk_types import MarketState, PortfolioState, RiskDecision, TradeIntent


class RiskEngine:
    def __init__(self, profile: Dict[str, Any]):
        self.profile = profile

    def evaluate(self, portfolio: PortfolioState, market: MarketState, intent: TradeIntent) -> RiskDecision:
        reasons: List[str] = []
        metrics: Dict[str, float] = {}
        guards = self.profile.get("guards", {})
        portfolio_limits = self.profile.get("portfolio", {})
        market_limits = self.profile.get("market", {})
        execution = self.profile.get("execution", {})
        dca = self.profile.get("dca", {})

        def add_metric(name: str, value: float) -> None:
            metrics[name] = float(value)

        add_metric("daily_pnl_ratio", portfolio.daily_pnl_ratio)
        add_metric("weekly_pnl_ratio", portfolio.weekly_pnl_ratio)
        add_metric("drawdown_ratio", portfolio.drawdown_ratio)
        add_metric("realized_volatility_ratio", market.realized_volatility_ratio)
        add_metric("funding_rate", market.funding_rate)

        if portfolio.daily_pnl_ratio <= -guards.get("daily_loss_limit_ratio", 1.0):
            reasons.append("daily loss limit breached")
        if portfolio.weekly_pnl_ratio <= -guards.get("weekly_loss_limit_ratio", 1.0):
            reasons.append("weekly loss limit breached")
        if portfolio.drawdown_ratio >= guards.get("max_drawdown_ratio", 1.0):
            reasons.append("max drawdown breached")
        if portfolio.consecutive_losses >= guards.get("consecutive_loss_limit", 999):
            reasons.append("consecutive loss limit breached")

        if portfolio.total_exposure >= portfolio_limits.get("max_total_exposure_ratio", 1.0):
            reasons.append("total exposure limit breached")
        if portfolio.strategy_exposure >= portfolio_limits.get("max_strategy_exposure_ratio", 1.0):
            reasons.append("strategy exposure limit breached")
        if portfolio.symbol_exposure >= portfolio_limits.get("max_symbol_exposure_ratio", 1.0):
            reasons.append("symbol exposure limit breached")
        if portfolio.correlated_bucket_exposure >= portfolio_limits.get("max_correlated_bucket_exposure_ratio", 1.0):
            reasons.append("correlated bucket exposure limit breached")
        if portfolio.open_positions >= portfolio_limits.get("max_open_positions", 999):
            reasons.append("open positions limit breached")

        if market.realized_volatility_ratio >= market_limits.get("max_market_volatility_ratio", 1.0):
            reasons.append("market volatility too high")
        if abs(market.funding_rate) >= market_limits.get("max_funding_rate_abs", 999.0):
            reasons.append("funding rate too high")
        if market.broad_market_drop_ratio >= market_limits.get("broad_market_drop_ratio", 999.0):
            reasons.append("broad market stress")
        if execution.get("require_scanner_approval", False) and not market.scanner_approved:
            reasons.append("scanner approval missing")

        if intent.proposed_slippage_ratio > execution.get("max_slippage_ratio", 1.0):
            reasons.append("expected slippage too high")
        if execution.get("reject_orders_without_stop", False) and not intent.has_stoploss:
            reasons.append("missing stoploss")
        if intent.order_value < execution.get("min_notional_per_trade", 0.0):
            reasons.append("order value below minimum notional")

        if intent.additional_entry_index > 0:
            if not dca.get("enabled", False):
                reasons.append("dca disabled")
            if intent.additional_entry_index > dca.get("max_additional_entries", 0):
                reasons.append("too many additional entries")

        if reasons:
            reduce_only_conditions = {
                "market volatility too high",
                "broad market stress",
                "scanner approval missing",
            }
            mode = "reduce_only" if any(r in reduce_only_conditions for r in reasons) else "block"
            return RiskDecision(
                allow=False,
                mode=mode,
                reasons=reasons,
                metrics=metrics,
                cooldown_minutes=guards.get("cooldown_minutes_after_guard_trip"),
            )

        return RiskDecision(allow=True, mode="allow", reasons=[], metrics=metrics)
