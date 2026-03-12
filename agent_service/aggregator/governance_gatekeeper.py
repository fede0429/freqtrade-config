from __future__ import annotations

from typing import Dict, Any


class GovernanceGatekeeper:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "require_provider_gate_passed": True,
                "require_no_blocking_anomaly": True,
                "require_no_active_cooldown": False,
                "default_trading_mode": "shadow_only",
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
        provider_gate: Dict[str, Any],
        anomaly_guard: Dict[str, Any],
        cooldown_guard: Dict[str, Any],
        execution_policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        cfg = self.config_for_pair(pair)
        reasons = []

        if bool(cfg.get("require_provider_gate_passed", True)) and not bool(provider_gate.get("provider_gate_passed", False)):
            reasons.append("provider_gate_failed")
        if bool(cfg.get("require_no_blocking_anomaly", True)) and bool(anomaly_guard.get("blocking", False)):
            reasons.append("blocking_anomaly")
        if bool(cfg.get("require_no_active_cooldown", False)) and bool(cooldown_guard.get("active", False)):
            reasons.append("active_cooldown")

        approved = len(reasons) == 0
        trading_mode = "shadow_only"
        if approved:
            trading_mode = str(cfg.get("approved_trading_mode", "paper_candidate"))
        else:
            trading_mode = str(cfg.get("blocked_trading_mode", cfg.get("default_trading_mode", "shadow_only")))

        return {
            "approved": approved,
            "reasons": reasons,
            "trading_mode": trading_mode,
            "execution_policy_snapshot": execution_policy,
        }
