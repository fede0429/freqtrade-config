from agent_service.providers.provider_base import ProviderHealth, ProviderSnapshot, utc_now_iso

class DexPaprikaProvider:
    name = "dexpaprika"
    kind = "onchain_liquidity"

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, kind=self.kind, status="ok", ts=utc_now_iso(), detail="snapshot_provider")

    def supports_pair(self, pair: str) -> bool:
        return "/" in pair

    def fetch(self, pair: str, context=None) -> ProviderSnapshot:
        signals = {"liquidity_usd": 2450000, "pool_count": 14, "slippage_risk": "low", "dex_activity": "elevated"}
        return ProviderSnapshot(provider=self.name, kind=self.kind, pair=pair, status="ok", ts=utc_now_iso(), latency_ms=250, stale=False, score=0.68, signals=signals, risk_flags=[], raw_ref={"source": self.name})
