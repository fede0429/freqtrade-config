from agent_service.providers.provider_base import ProviderHealth, ProviderSnapshot, utc_now_iso

class TradingViewMcpProvider:
    name = "tradingview_mcp"
    kind = "market_data"

    def __init__(self, default_timeframe: str = "1h") -> None:
        self.default_timeframe = default_timeframe

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, kind=self.kind, status="ok", ts=utc_now_iso(), detail="snapshot_provider")

    def supports_pair(self, pair: str) -> bool:
        return "/" in pair

    def fetch(self, pair: str, context=None) -> ProviderSnapshot:
        timeframe = (context or {}).get("timeframe", self.default_timeframe)
        signals = {"trend": "bullish", "rsi": 62.5, "macd_bias": "positive", "volatility_regime": "medium", "timeframe": timeframe}
        return ProviderSnapshot(provider=self.name, kind=self.kind, pair=pair, status="ok", ts=utc_now_iso(), latency_ms=200, stale=False, score=0.76, signals=signals, risk_flags=[], raw_ref={"source": self.name})
