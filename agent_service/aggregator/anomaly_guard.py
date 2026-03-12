from __future__ import annotations

from typing import Any, Dict, List

from agent_service.providers.provider_base import ProviderSnapshot


class AnomalyGuard:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "max_provider_latency_ms": 1200,
                "max_score_drift": 0.45,
                "block_on_high_latency": False,
                "block_on_high_drift": True,
                "block_on_risk_flags": ["high_slippage_risk"],
            },
        )

    def pair_overrides(self) -> Dict[str, Any]:
        raw = self.config.get("pair_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}

    def config_for_pair(self, pair: str) -> Dict[str, Any]:
        cfg = dict(self.global_defaults())
        cfg.update(self.pair_overrides().get(pair.upper(), {}))
        return cfg

    def check_pair(self, pair: str, snapshots: List[ProviderSnapshot]) -> Dict[str, Any]:
        cfg = self.config_for_pair(pair)
        max_latency = int(cfg.get("max_provider_latency_ms", 1200))
        max_score_drift = float(cfg.get("max_score_drift", 0.45))
        blocked_flags = set(cfg.get("block_on_risk_flags", ["high_slippage_risk"]))
        block_on_high_latency = bool(cfg.get("block_on_high_latency", False))
        block_on_high_drift = bool(cfg.get("block_on_high_drift", True))

        issues: List[dict] = []
        scores = [float(s.score) for s in snapshots]
        drift = (max(scores) - min(scores)) if len(scores) >= 2 else 0.0

        for s in snapshots:
            if s.latency_ms > max_latency:
                issues.append(
                    {
                        "provider": s.provider,
                        "kind": "high_latency",
                        "value": s.latency_ms,
                        "threshold": max_latency,
                        "blocking": block_on_high_latency,
                    }
                )
            flagged = [flag for flag in s.risk_flags if flag in blocked_flags]
            if flagged:
                issues.append(
                    {
                        "provider": s.provider,
                        "kind": "risk_flags",
                        "value": flagged,
                        "threshold": list(blocked_flags),
                        "blocking": True,
                    }
                )

        if drift > max_score_drift:
            issues.append(
                {
                    "provider": "multi_provider",
                    "kind": "score_drift",
                    "value": round(drift, 4),
                    "threshold": max_score_drift,
                    "blocking": block_on_high_drift,
                }
            )

        blocking = any(bool(i.get("blocking", False)) for i in issues)
        return {
            "pair": pair,
            "issues": issues,
            "blocking": blocking,
            "score_drift": round(drift, 4),
        }
