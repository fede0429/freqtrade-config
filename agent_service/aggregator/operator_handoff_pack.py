from __future__ import annotations

from typing import Dict, Any


def build_operator_handoff_pack(decision_cache: Dict[str, Any]) -> Dict[str, Any]:
    pairs = {}
    for pair, meta in decision_cache.get("pairs", {}).items():
        pairs[pair] = {
            "trading_mode": meta.get("trading_mode"),
            "rollout_state": meta.get("rollout_state"),
            "governance_gate": meta.get("governance_gate"),
            "governance_gatekeeper": meta.get("governance_gatekeeper"),
            "rollout_state_machine": meta.get("rollout_state_machine"),
            "execution_policy": meta.get("execution_policy"),
            "anomaly_guard": meta.get("anomaly_guard"),
            "cooldown_guard": meta.get("cooldown_guard"),
            "confidence": meta.get("confidence"),
            "risk_score": meta.get("risk_score"),
            "entry_allowed": meta.get("entry_allowed"),
            "stake_multiplier": meta.get("stake_multiplier"),
            "target_rr": meta.get("target_rr"),
            "providers": meta.get("providers"),
            "trace": meta.get("trace"),
        }
    return {
        "ts": decision_cache.get("ts"),
        "schema_version": decision_cache.get("schema_version"),
        "source": decision_cache.get("source"),
        "pairs": pairs,
    }
