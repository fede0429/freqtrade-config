from __future__ import annotations

from typing import Dict, Any


class ConfidencePolicy:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "entry_min_confidence": 0.75,
                "max_risk_score": 0.40,
                "neutralize_degraded_provider_score": True,
            },
        )

    def pair_overrides(self) -> Dict[str, Any]:
        raw = self.config.get("pair_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}

    def provider_weights(self) -> Dict[str, float]:
        raw = self.config.get("provider_weights", {})
        return {str(k): float(v) for k, v in raw.items()}

    def config_for_pair(self, pair: str) -> Dict[str, Any]:
        pair = pair.upper()
        cfg = dict(self.global_defaults())
        cfg.update(self.pair_overrides().get(pair, {}))
        return cfg

    def weight_for_provider(self, provider_name: str) -> float:
        return float(self.provider_weights().get(provider_name, 1.0))
