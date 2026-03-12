from __future__ import annotations

from typing import Any, Dict, Optional

from agent_service.providers.provider_base import (
    MarketDataProvider,
    ProviderHealth,
    ProviderSnapshot,
    utc_now_iso,
)


class TradingViewMcpProvider(MarketDataProvider):
    name = "tradingview_mcp"

    def __init__(self, default_timeframe: str = "1h") -> None:
        self.default_timeframe = default_timeframe

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            kind=self.kind,
            status="ok",
            ts=utc_now_iso(),
            detail="snapshot_provider",
        )

    def supports_pair(self, pair: str) -> bool:
        return "/" in pair

    def _call_mcp_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "trend": "bullish",
            "rsi": 62.5,
            "macd_bias": "positive",
            "volatility_regime": "medium",
        }

    def fetch(self, pair: str, context: Optional[Dict[str, Any]] = None) -> ProviderSnapshot:
        timeframe = (context or {}).get("timeframe", self.default_timeframe)
        return self.fetch_technical_snapshot(pair, timeframe, context=context)

    def fetch_technical_snapshot(
        self, pair: str, timeframe: str, context: Optional[Dict[str, Any]] = None
    ) -> ProviderSnapshot:
        symbol = pair.replace("/", "")
        signals = self._call_mcp_tool("get_indicators", {"symbol": symbol, "timeframe": timeframe})
        trend = signals.get("trend", "neutral")
        score = 0.50
        if trend == "bullish":
            score = 0.76
        elif trend == "bearish":
            score = 0.24

        risk_flags = []
        if signals.get("volatility_regime") == "high":
            risk_flags.append("high_volatility")

        return ProviderSnapshot(
            provider=self.name,
            kind=self.kind,
            pair=pair,
            status="ok",
            ts=utc_now_iso(),
            latency_ms=200,
            stale=False,
            score=score,
            signals=signals,
            risk_flags=risk_flags,
            raw_ref={"tool": "get_indicators", "source": self.name, "timeframe": timeframe},
        )
