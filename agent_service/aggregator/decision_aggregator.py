from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from agent_service.providers.provider_base import ProviderSnapshot
from agent_service.aggregator.confidence_policy import ConfidencePolicy


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionAggregator:
    def __init__(
        self,
        cache_ttl_seconds: int = 90,
        shadow_mode: bool = True,
        confidence_policy: dict | None = None,
    ) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self.shadow_mode = shadow_mode
        self.policy = ConfidencePolicy(confidence_policy or {})

    def _weighted_scores(self, snapshots: Iterable[ProviderSnapshot], pair: str) -> List[float]:
        cfg = self.policy.config_for_pair(pair)
        neutralize_degraded = bool(cfg.get("neutralize_degraded_provider_score", True))
        values: List[float] = []
        for s in snapshots:
            score = max(0.0, min(1.0, float(s.score)))
            if s.status == "degraded" and neutralize_degraded:
                score = 0.50
            weight = self.policy.weight_for_provider(s.provider)
            values.append(score * max(weight, 0.0))
        return values

    def _confidence_from_snapshots(self, snapshots: Iterable[ProviderSnapshot], pair: str) -> float:
        snaps = list(snapshots)
        if not snaps:
            return 0.0
        weighted = self._weighted_scores(snaps, pair)
        total_weight = sum(max(self.policy.weight_for_provider(s.provider), 0.0) for s in snaps)
        if total_weight <= 0:
            return 0.0
        return round(sum(weighted) / total_weight, 4)

    def _risk_score_from_snapshots(self, snapshots: Iterable[ProviderSnapshot], pair: str) -> float:
        flags = sum(len(s.risk_flags) for s in snapshots)
        base = min(flags * 0.1, 0.8)
        cfg = self.policy.config_for_pair(pair)
        bias = float(cfg.get("risk_bias", 0.0))
        return round(max(0.0, min(base + bias, 1.0)), 4)

    def _market_regime(self, snapshots: Iterable[ProviderSnapshot]) -> str:
        for s in snapshots:
            trend = s.signals.get("trend")
            if trend == "bullish":
                return "trend"
            if trend == "bearish":
                return "downtrend"
        return "range"

    def build_pair_decision(self, pair: str, snapshots: List[ProviderSnapshot]) -> Dict[str, Any]:
        cfg = self.policy.config_for_pair(pair)
        confidence = self._confidence_from_snapshots(snapshots, pair)
        risk_score = self._risk_score_from_snapshots(snapshots, pair)
        regime = self._market_regime(snapshots)

        entry_min_confidence = float(cfg.get("entry_min_confidence", 0.75))
        max_risk_score = float(cfg.get("max_risk_score", 0.40))
        entry_allowed = confidence >= entry_min_confidence and risk_score <= max_risk_score

        stake_multiplier = 1.0
        if confidence >= max(entry_min_confidence + 0.05, 0.80) and regime == "trend":
            stake_multiplier = float(cfg.get("trend_high_conf_stake_multiplier", 1.35))
        elif confidence >= entry_min_confidence:
            stake_multiplier = float(cfg.get("base_live_stake_multiplier", 1.15))

        target_rr = float(cfg.get("base_target_rr", 1.8))
        if regime == "trend":
            target_rr = float(cfg.get("trend_target_rr", 2.8))

        agent_stoploss = float(cfg.get("base_agent_stoploss", -0.045))
        if confidence >= max(entry_min_confidence + 0.05, 0.80):
            agent_stoploss = float(cfg.get("high_conf_agent_stoploss", -0.035))

        providers = {
            s.provider: {
                "status": s.status,
                "score": s.score,
                "ts": s.ts,
                "stale": s.stale,
                "weight": self.policy.weight_for_provider(s.provider),
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
                "entry_reason": "weighted_multi_skill_alignment" if entry_allowed else "confidence_or_risk_blocked",
                "entry_min_confidence": entry_min_confidence,
            },
            "stake": {
                "stake_multiplier": stake_multiplier,
                "stake_cap_ratio": float(cfg.get("stake_cap_ratio", 0.12)),
                "stake_reason": "weighted_provider_signal",
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
                "roi_min_trade_duration": int(cfg.get("roi_min_trade_duration", 5)),
            },
            "trace": {
                "decision_id": f"dec_{pair.replace('/', '_').lower()}_{utc_now_iso().replace(':', '').replace('-', '')}",
                "evidence_refs": [f"{s.provider}:{pair}" for s in snapshots],
                "policy_snapshot": cfg,
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
