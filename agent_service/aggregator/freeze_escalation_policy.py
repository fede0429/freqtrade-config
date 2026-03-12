from __future__ import annotations

from typing import Dict, Any


class FreezeEscalationPolicy:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "freeze_on_hold_verdict": True,
                "escalate_on_review_verdict": True,
                "escalate_on_blocking_anomaly": True,
                "escalate_on_active_cooldown": False,
                "default_action": "continue_shadow",
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
        readiness: Dict[str, Any],
        anomaly_guard: Dict[str, Any],
        cooldown_guard: Dict[str, Any],
        rollout_state_machine: Dict[str, Any],
    ) -> Dict[str, Any]:
        cfg = self.config_for_pair(pair)
        verdict = str(readiness.get("verdict", "hold"))
        reasons = []

        freeze = False
        escalate = False

        if verdict == "hold" and bool(cfg.get("freeze_on_hold_verdict", True)):
            freeze = True
            reasons.append("freeze_on_hold_verdict")

        if verdict == "review" and bool(cfg.get("escalate_on_review_verdict", True)):
            escalate = True
            reasons.append("escalate_on_review_verdict")

        if bool(anomaly_guard.get("blocking", False)) and bool(cfg.get("escalate_on_blocking_anomaly", True)):
            escalate = True
            reasons.append("escalate_on_blocking_anomaly")

        if bool(cooldown_guard.get("active", False)) and bool(cfg.get("escalate_on_active_cooldown", False)):
            escalate = True
            reasons.append("escalate_on_active_cooldown")

        if bool(rollout_state_machine.get("frozen", False)):
            freeze = True
            reasons.append("freeze_on_rollout_state")

        action = cfg.get("default_action", "continue_shadow")
        if freeze:
            action = "freeze_pair"
        elif escalate:
            action = "escalate_for_review"
        elif verdict == "go":
            action = "ready_for_snapshot"

        return {
            "freeze": freeze,
            "escalate": escalate,
            "action": action,
            "reasons": reasons,
        }
