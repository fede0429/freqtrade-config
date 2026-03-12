from __future__ import annotations

from typing import Dict, Any


class RolloutStateMachine:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "mode_to_state": {
                    "shadow_only": "shadow",
                    "technical_shadow": "shadow",
                    "candidate_shadow": "candidate",
                    "paper_candidate": "paper",
                    "paper_ready": "paper",
                    "limited_live_candidate": "limited_live"
                },
                "promote_when_governance_approved": True,
                "freeze_on_active_cooldown": True,
                "freeze_on_blocking_anomaly": True,
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
        anomaly_guard: Dict[str, Any],
        cooldown_guard: Dict[str, Any],
        execution_policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        cfg = self.config_for_pair(pair)
        mode_to_state = cfg.get("mode_to_state", {})
        trading_mode = str(governance_gatekeeper.get("trading_mode", "shadow_only"))
        rollout_state = str(mode_to_state.get(trading_mode, "shadow"))

        recommendations = []
        frozen = False

        if bool(cfg.get("freeze_on_blocking_anomaly", True)) and bool(anomaly_guard.get("blocking", False)):
            frozen = True
            recommendations.append("freeze_due_to_blocking_anomaly")
        if bool(cfg.get("freeze_on_active_cooldown", True)) and bool(cooldown_guard.get("active", False)):
            frozen = True
            recommendations.append("freeze_due_to_active_cooldown")

        approved = bool(governance_gatekeeper.get("approved", False))
        if approved and bool(cfg.get("promote_when_governance_approved", True)) and not frozen:
            if rollout_state == "shadow":
                recommendations.append("promote_to_candidate")
            elif rollout_state == "candidate":
                recommendations.append("promote_to_paper")
            elif rollout_state == "paper":
                recommendations.append("consider_limited_live")

        if not approved and rollout_state in {"paper", "limited_live"}:
            recommendations.append("demote_to_shadow")

        provider_gate_passed = bool(execution_policy.get("provider_gate_passed", False))
        readiness_score = 0
        if provider_gate_passed:
            readiness_score += 1
        if approved:
            readiness_score += 1
        if not bool(anomaly_guard.get("blocking", False)):
            readiness_score += 1
        if not bool(cooldown_guard.get("active", False)):
            readiness_score += 1

        return {
            "rollout_state": rollout_state,
            "trading_mode": trading_mode,
            "frozen": frozen,
            "recommendations": recommendations,
            "readiness_score": readiness_score,
        }
