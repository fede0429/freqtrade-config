from __future__ import annotations

from typing import Any, Dict, Optional

from agent_service.providers.provider_base import (
    OnchainLiquidityProvider,
    ProviderHealth,
    ProviderSnapshot,
    utc_now_iso,
)


class DexPaprikaProvider(OnchainLiquidityProvider):
    name = "dexpaprika"

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            kind=self.kind,
            status="ok",
            ts=utc_now_iso(),
            detail="skeleton_provider",
        )

    def supports_pair(self, pair: str) -> bool:
        return "/" in pair

    def _fetch_dex_snapshot(self, pair: str) -> Dict[str, Any]:
        return {
            "liquidity_usd": 2450000,
            "pool_count": 14,
            "slippage_risk": "low",
            "dex_activity": "elevated",
        }

    def fetch(self, pair: str, context: Optional[Dict[str, Any]] = None) -> ProviderSnapshot:
        return self.fetch_liquidity_snapshot(pair, context=context)

    def fetch_liquidity_snapshot(
        self, pair: str, context: Optional[Dict[str, Any]] = None
    ) -> ProviderSnapshot:
        signals = self._fetch_dex_snapshot(pair)

        liquidity_usd = float(signals.get("liquidity_usd", 0))
        score = 0.40
        if liquidity_usd >= 2000000:
            score = 0.68
        elif liquidity_usd >= 500000:
            score = 0.56

        risk_flags = []
        if signals.get("slippage_risk") == "high":
            risk_flags.append("high_slippage_risk")
        if liquidity_usd < 250000:
            risk_flags.append("thin_liquidity")

        return ProviderSnapshot(
            provider=self.name,
            kind=self.kind,
            pair=pair,
            status="ok",
            ts=utc_now_iso(),
            latency_ms=250,
            stale=False,
            score=score,
            signals=signals,
            risk_flags=risk_flags,
            raw_ref={
                "tool": "dex_liquidity_snapshot",
                "source": self.name,
            },
        )
