from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from agent_service.providers.provider_base import ProviderSnapshot


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionAggregator:
    def __init__(self, cache_ttl_seconds: int = 90, shadow_mode: bool = True) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self.shadow_mode = shadow_mode

    def _confidence_from_snapshots(self, snapshots: Iterable[ProviderSnapshot]) -> float:
        values = [max(0.0, min(1.0, s.score)) for s in snapshots]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)

    def _risk_score_from_snapshots(self, snapshots: Iterable[ProviderSnapshot]) -> float:
        flags = sum(len(s.risk_flags) for s in snapshots)
        return round(min(flags * 0.1, 0.8), 4)

    def _market_regime(self, snapshots: Iterable[ProviderSnapshot]) -> str:
        for s in snapshots:
            trend = s.signals.get("trend")
            if trend == "bullish":
                return "trend"
            if trend == "bearish":
                return "downtrend"
        return "range"

    def build_pair_decision(self, pair: str, snapshots: List[ProviderSnapshot]) -> Dict[str, Any]:
        confidence = self._confidence_from_snapshots(snapshots)
        risk_score = self._risk_score_from_snapshots(snapshots)
        regime = self._market_regime(snapshots)

        entry_allowed = confidence >= 0.75 and risk_score <= 0.40
        stake_multiplier = 1.0
        if confidence >= 0.80 and regime == "trend":
            stake_multiplier = 1.35
        elif confidence >= 0.72:
            stake_multiplier = 1.15

        target_rr = 2.8 if regime == "trend" else 1.8
        agent_stoploss = -0.035 if confidence >= 0.80 else -0.045

        providers = {
            s.provider: {
                "status": s.status,
                "score": s.score,
                "ts": s.ts,
                "stale": s.stale,
            }
            for s in snapshots
        }

        return {
            "agent_enabled": True,
            "pair_enabled": True,
            "governance_gate": "passed",
            "market_regime": regime,
            "confidence": confidence,
            "risk_score": risk_score,
            "providers": providers,
            "entry": {
                "entry_allowed": entry_allowed,
                "entry_reason": "multi_skill_alignment" if entry_allowed else "confidence_or_risk_blocked",
                "entry_min_confidence": 0.75,
            },
            "stake": {
                "stake_multiplier": stake_multiplier,
                "stake_cap_ratio": 0.12,
                "stake_reason": "aggregated_provider_signal",
            },
            "exit": {
                "exit_signal": False,
                "exit_reason": None,
                "force_exit_on_loss": False,
            },
            "stoploss": {
                "stoploss_mode": "tighten_only",
                "agent_stoploss": agent_stoploss,
            },
            "roi": {
                "target_rr": target_rr,
                "roi_min_trade_duration": 5,
            },
            "trace": {
                "decision_id": f"dec_{pair.replace('/', '_').lower()}_{utc_now_iso().replace(':', '').replace('-', '')}",
                "evidence_refs": [f"{s.provider}:{pair}" for s in snapshots],
            },
            "entry_allowed": entry_allowed,
            "stake_multiplier": stake_multiplier,
            "exit_signal": False,
            "exit_reason": None,
            "stoploss_mode": "tighten_only",
            "agent_stoploss": agent_stoploss,
            "target_rr": target_rr,
        }

    def build_decision_cache(self, pair_snapshots: Dict[str, List[ProviderSnapshot]]) -> Dict[str, Any]:
        pairs = {}
        for pair, snapshots in pair_snapshots.items():
            pairs[pair] = self.build_pair_decision(pair, snapshots)

        return {
            "schema_version": "2.0",
            "ts": utc_now_iso(),
            "source": "decision_aggregator",
            "env": "dry-run",
            "global": {
                "shadow_mode": self.shadow_mode,
                "governance_gate": "passed",
                "cache_ttl_seconds": self.cache_ttl_seconds,
                "aggregator_health": "ok",
                "fallback_mode": "base_strategy_only",
            },
            "pairs": pairs,
        }

    def write_decision_cache(
        self,
        pair_snapshots: Dict[str, List[ProviderSnapshot]],
        output_path: str = "user_data/agent_runtime/state/decision_cache.json",
    ) -> Path:
        payload = self.build_decision_cache(pair_snapshots)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return out


if __name__ == "__main__":
    from agent_service.providers.market_data.tradingview_mcp_provider import TradingViewMcpProvider
    from agent_service.providers.onchain.dexpaprika_provider import DexPaprikaProvider

    tv = TradingViewMcpProvider(default_timeframe="1h")
    dex = DexPaprikaProvider()

    pair_snapshots = {
        "BTC/USDT": [tv.fetch("BTC/USDT", {"timeframe": "1h"}), dex.fetch("BTC/USDT")],
        "ETH/USDT": [tv.fetch("ETH/USDT", {"timeframe": "1h"}), dex.fetch("ETH/USDT")],
    }

    out = DecisionAggregator().write_decision_cache(pair_snapshots)
    print(out)
