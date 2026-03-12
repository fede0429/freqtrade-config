from __future__ import annotations

from typing import Dict, Any


class ExecutionPolicy:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "min_provider_count": 1,
                "fallback_mode": "base_strategy_only",
                "allow_entry_confirm": True,
                "allow_stake": True,
                "allow_exit": True,
                "allow_stoploss": True,
                "allow_roi": True,
            },
        )

    def pair_overrides(self) -> Dict[str, Any]:
        raw = self.config.get("pair_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}

    def config_for_pair(self, pair: str) -> Dict[str, Any]:
        pair = pair.upper()
        cfg = dict(self.global_defaults())
        cfg.update(self.pair_overrides().get(pair, {}))
        return cfg

    def callback_policy(self, pair: str) -> Dict[str, bool]:
        cfg = self.config_for_pair(pair)
        return {
            "entry_confirm": bool(cfg.get("allow_entry_confirm", True)),
            "stake": bool(cfg.get("allow_stake", True)),
            "exit": bool(cfg.get("allow_exit", True)),
            "stoploss": bool(cfg.get("allow_stoploss", True)),
            "roi": bool(cfg.get("allow_roi", True)),
        }
