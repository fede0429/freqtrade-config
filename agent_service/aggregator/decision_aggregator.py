from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from agent_service.providers.provider_base import ProviderSnapshot
from agent_service.aggregator.confidence_policy import ConfidencePolicy
from agent_service.aggregator.execution_policy import ExecutionPolicy
from agent_service.aggregator.anomaly_guard import AnomalyGuard
from agent_service.aggregator.cooldown_guard import CooldownGuard
from agent_service.aggregator.governance_gatekeeper import GovernanceGatekeeper


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionAggregator:
    def __init__(
        self,
        cache_ttl_seconds: int = 90,
        shadow_mode: bool = True,
        confidence_policy: dict | None = None,
        execution_policy: dict | None = None,
        anomaly_policy: dict | None = None,
        cooldown_policy: dict | None = None,
        governance_policy: dict | None = None,
    ) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self.shadow_mode = shadow_mode
        self.policy = ConfidencePolicy(confidence_policy or {})
        self.execution_policy = ExecutionPolicy(execution_policy or {})
        self.anomaly_guard = AnomalyGuard(anomaly_policy or {})
        self.cooldown_guard = CooldownGuard(cooldown_policy or {})
        self.governance_gatekeeper = GovernanceGatekeeper(governance_policy or {})

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

    def _provider_summary(self, snapshots: List[ProviderSnapshot]) -> dict:
        return {
            s.provider: {
                "status": s.status,
                "score": s.score,
                "ts": s.ts,
                "stale": s.stale,
                "weight": self.policy.weight_for_provider(s.provider),
                "latency_ms": s.latency_ms,
                "risk_flags": s.risk_flags,
            }
            for s in snapshots
        }

    def _provider_gate(self, pair: str, snapshots: List[ProviderSnapshot]) -> dict:
        cfg = self.execution_policy.config_for_pair(pair)
        min_provider_count = int(cfg.get("min_provider_count", 1))
        available = len(snapshots)
        provider_gate_passed = available >= min_provider_count
        return {
            "provider_gate_passed": provider_gate_passed,
            "available_provider_count": available,
            "min_provider_count": min_provider_count,
            "fallback_mode": cfg.get("fallback_mode", "base_strategy_only"),
        }

    def build_pair_decision(self, pair: str, snapshots: List[ProviderSnapshot]) -> Dict[str, Any]:
        cfg = self.policy.config_for_pair(pair)
        callback_policy = self.execution_policy.callback_policy(pair)
        provider_gate = self._provider_gate(pair, snapshots)
        anomaly = self.anomaly_guard.check_pair(pair, snapshots)
        cooldown = self.cooldown_guard.maybe_enter_cooldown(
            pair,
            anomaly_blocking=bool(anomaly["blocking"]),
            provider_gate_passed=bool(provider_gate["provider_gate_passed"]),
        )
        governance = self.governance_gatekeeper.evaluate(
            pair=pair,
            provider_gate=provider_gate,
            anomaly_guard=anomaly,
            cooldown_guard=cooldown,
            execution_policy=callback_policy,
        )

        confidence = self._confidence_from_snapshots(snapshots, pair)
        risk_score = self._risk_score_from_snapshots(snapshots, pair)
        regime = self._market_regime(snapshots)

        entry_min_confidence = float(cfg.get("entry_min_confidence", 0.75))
        max_risk_score = float(cfg.get("max_risk_score", 0.40))
        entry_allowed_raw = (
            provider_gate["provider_gate_passed"]
            and not anomaly["blocking"]
            and confidence >= entry_min_confidence
            and risk_score <= max_risk_score
        )
        entry_allowed = self.cooldown_guard.apply_entry_policy(pair, entry_allowed_raw)
        entry_allowed = entry_allowed and bool(governance.get("approved", False))

        stake_multiplier = 1.0
        if confidence >= max(entry_min_confidence + 0.05, 0.80) and regime == "trend":
            stake_multiplier = float(cfg.get("trend_high_conf_stake_multiplier", 1.35))
        elif confidence >= entry_min_confidence:
            stake_multiplier = float(cfg.get("base_live_stake_multiplier", 1.15))
        stake_multiplier = self.cooldown_guard.apply_stake_multiplier_cap(pair, stake_multiplier)

        target_rr = float(cfg.get("base_target_rr", 1.8))
        if regime == "trend":
            target_rr = float(cfg.get("trend_target_rr", 2.8))

        agent_stoploss = float(cfg.get("base_agent_stoploss", -0.045))
        if confidence >= max(entry_min_confidence + 0.05, 0.80):
            agent_stoploss = float(cfg.get("high_conf_agent_stoploss", -0.035))

        providers = self._provider_summary(snapshots)

        return {
            "agent_enabled": provider_gate["provider_gate_passed"] and not anomaly["blocking"] and bool(governance.get("approved", False)),
            "pair_enabled": True,
            "governance_gate": "passed" if governance.get("approved", False) else "blocked",
            "governance_gatekeeper": governance,
            "market_regime": regime,
            "confidence": confidence,
            "risk_score": risk_score,
            "providers": providers,
            "execution_policy": {**callback_policy, **provider_gate},
            "anomaly_guard": anomaly,
            "cooldown_guard": cooldown,
            "entry": {
                "entry_allowed": entry_allowed and callback_policy["entry_confirm"],
                "entry_reason": "governed_provider_alignment" if entry_allowed else "governance_or_provider_or_anomaly_or_confidence_or_risk_or_cooldown_blocked",
                "entry_min_confidence": entry_min_confidence,
            },
            "stake": {
                "stake_multiplier": stake_multiplier if callback_policy["stake"] and governance.get("approved", False) else 1.0,
                "stake_cap_ratio": float(cfg.get("stake_cap_ratio", 0.12)),
                "stake_reason": "weighted_provider_signal" if callback_policy["stake"] and governance.get("approved", False) else "stake_disabled_by_governance_or_execution_policy",
            },
            "exit": {
                "exit_signal": False,
                "exit_reason": None,
                "force_exit_on_loss": False,
                "callback_enabled": callback_policy["exit"],
            },
            "stoploss": {
                "stoploss_mode": "tighten_only" if callback_policy["stoploss"] else "disabled",
                "agent_stoploss": agent_stoploss if callback_policy["stoploss"] else None,
            },
            "roi": {
                "target_rr": target_rr if callback_policy["roi"] and governance.get("approved", False) else None,
                "roi_min_trade_duration": int(cfg.get("roi_min_trade_duration", 5)),
                "callback_enabled": callback_policy["roi"],
            },
            "trace": {
                "decision_id": f"dec_{pair.replace('/', '_').lower()}_{utc_now_iso().replace(':', '').replace('-', '')}",
                "evidence_refs": [f"{s.provider}:{pair}" for s in snapshots],
                "policy_snapshot": cfg,
                "execution_snapshot": callback_policy,
                "anomaly_snapshot": anomaly,
                "cooldown_snapshot": cooldown,
                "governance_snapshot": governance,
            },
            "trading_mode": governance.get("trading_mode", "shadow_only"),
            "entry_allowed": entry_allowed and callback_policy["entry_confirm"],
            "stake_multiplier": stake_multiplier if callback_policy["stake"] and governance.get("approved", False) else 1.0,
            "exit_signal": False,
            "exit_reason": None,
            "stoploss_mode": "tighten_only" if callback_policy["stoploss"] else "disabled",
            "agent_stoploss": agent_stoploss if callback_policy["stoploss"] else None,
            "target_rr": target_rr if callback_policy["roi"] and governance.get("approved", False) else None,
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
