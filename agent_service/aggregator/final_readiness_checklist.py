from __future__ import annotations

from typing import Dict, Any


class FinalReadinessChecklist:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "min_readiness_score": 3,
                "require_governance_approved": True,
                "require_rollout_not_frozen": True,
                "require_provider_gate_passed": True,
                "require_no_blocking_anomaly": True,
            },
        )

    def pair_overrides(self) -> Dict[str, Any]:
        raw = self.config.get("pair_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}

    def config_for_pair(self, pair: str) -> Dict[str, Any]:
        cfg = dict(self.global_defaults())
        cfg.update(self.pair_overrides().get(pair.upper(), {}))
        return cfg

    def evaluate(
        self,
        pair: str,
        governance_gatekeeper: Dict[str, Any],
        rollout_state_machine: Dict[str, Any],
        execution_policy: Dict[str, Any],
        anomaly_guard: Dict[str, Any],
    ) -> Dict[str, Any]:
        cfg = self.config_for_pair(pair)
        reasons = []

        if bool(cfg.get("require_governance_approved", True)) and not bool(governance_gatekeeper.get("approved", False)):
            reasons.append("governance_not_approved")
        if bool(cfg.get("require_rollout_not_frozen", True)) and bool(rollout_state_machine.get("frozen", False)):
            reasons.append("rollout_frozen")
        if bool(cfg.get("require_provider_gate_passed", True)) and not bool(execution_policy.get("provider_gate_passed", False)):
            reasons.append("provider_gate_failed")
        if bool(cfg.get("require_no_blocking_anomaly", True)) and bool(anomaly_guard.get("blocking", False)):
            reasons.append("blocking_anomaly")

        readiness_score = int(rollout_state_machine.get("readiness_score", 0))
        min_readiness_score = int(cfg.get("min_readiness_score", 3))
        if readiness_score < min_readiness_score:
            reasons.append("readiness_score_below_threshold")

        verdict = "hold"
        if not reasons:
            verdict = "go"
        elif len(reasons) <= 2:
            verdict = "review"

        return {
            "verdict": verdict,
            "reasons": reasons,
            "readiness_score": readiness_score,
            "min_readiness_score": min_readiness_score,
        }
