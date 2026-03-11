from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

try:
    from user_data.strategies.SampleStrategy import SampleStrategy as BaseStrategy
except Exception:
    class BaseStrategy:
        timeframe = "5m"
        stoploss = -0.10
        process_only_new_candles = True
        use_custom_stoploss = True
        use_exit_signal = True

        def bot_loop_start(self, current_time, **kwargs):
            return None

        def custom_stake_amount(self, *args, **kwargs):
            return kwargs.get("proposed_stake")

        def custom_exit(self, *args, **kwargs):
            return None

        def custom_stoploss(self, *args, **kwargs):
            return None

        def custom_roi(self, *args, **kwargs):
            return None

        def confirm_trade_entry(self, *args, **kwargs):
            return True

class AgentBridgeStrategy(BaseStrategy):
    agent_overlay_path = Path("user_data/config/agent_overlay.json")
    decision_cache_path = Path("user_data/agent_runtime/state/decision_cache.json")
    bridge_state_path = Path("user_data/agent_runtime/state/bridge_state.json")
    use_custom_stoploss = True
    use_exit_signal = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent_overlay: dict[str, Any] = {}
        self._decision_cache: dict[str, Any] = {}
        self._load_overlay()
        self._load_decision_cache()

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _safe_read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _safe_write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_overlay(self) -> None:
        self._agent_overlay = self._safe_read_json(self.agent_overlay_path)

    def _load_decision_cache(self) -> None:
        self._decision_cache = self._safe_read_json(self.decision_cache_path)

    def _refresh_runtime_state(self) -> None:
        self._load_overlay()
        self._load_decision_cache()
        self._safe_write_json(
            self.bridge_state_path,
            {
                "bridge_refreshed_ts": self._utc_now(),
                "shadow_mode": self.shadow_mode,
                "enabled_callbacks": self.enabled_callbacks,
            },
        )

    @property
    def shadow_mode(self) -> bool:
        return bool(self._agent_overlay.get("shadow_mode", True))

    @property
    def enabled_callbacks(self) -> dict[str, bool]:
        return self._agent_overlay.get(
            "enabled_callbacks",
            {"stake": False, "exit": False, "stoploss": False, "roi": False, "entry_confirm": False},
        )

    def _pair_key(self, pair: str) -> str:
        return pair.upper()

    def _pair_decision(self, pair: str) -> dict[str, Any]:
        return self._decision_cache.get("pairs", {}).get(self._pair_key(pair), {})

    def _agent_enabled_for_pair(self, pair: str) -> bool:
        decision = self._pair_decision(pair)
        return bool(decision) and bool(decision.get("agent_enabled", False)) and decision.get("governance_gate") == "passed"

    def _log_shadow_event(self, kind: str, pair: str, payload: dict[str, Any]) -> None:
        log_path = Path("user_data/agent_runtime/state/shadow_log.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": self._utc_now(), "kind": kind, "pair": pair, "payload": payload}, ensure_ascii=False) + "\n")

    def bot_loop_start(self, current_time, **kwargs):
        try:
            self._refresh_runtime_state()
        except Exception:
            pass
        parent = getattr(super(), "bot_loop_start", None)
        if callable(parent):
            return parent(current_time, **kwargs)
        return None

    def custom_stake_amount(self, pair: str, current_time, current_rate: float, proposed_stake: float, min_stake, max_stake: float, leverage: float, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        if self.shadow_mode or not self.enabled_callbacks.get("stake", False):
            self._log_shadow_event("stake", pair, {"proposed_stake": proposed_stake, "decision": decision})
            return proposed_stake
        if not self._agent_enabled_for_pair(pair):
            return proposed_stake
        multiplier = min(float(decision.get("stake_multiplier", 1.0)), float(self._agent_overlay.get("max_stake_multiplier", 1.5)))
        if float(decision.get("confidence", 0.0)) < float(self._agent_overlay.get("min_confidence_for_live", 0.70)):
            return proposed_stake
        stake = proposed_stake * multiplier
        return min(stake, max_stake) if max_stake else stake

    def custom_exit(self, pair: str, trade, current_time, current_rate: float, current_profit: float, **kwargs):
        decision = self._pair_decision(pair)
        if self.shadow_mode or not self.enabled_callbacks.get("exit", False):
            self._log_shadow_event("exit", pair, {"current_profit": current_profit, "decision": decision})
            return None
        if self._agent_enabled_for_pair(pair) and bool(decision.get("exit_signal", False)):
            return decision.get("exit_reason", "agent_exit_signal")
        return None

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float, current_profit: float, after_fill: bool, **kwargs):
        decision = self._pair_decision(pair)
        if self.shadow_mode or not self.enabled_callbacks.get("stoploss", False):
            self._log_shadow_event("stoploss", pair, {"current_profit": current_profit, "decision": decision})
            return None
        if self._agent_enabled_for_pair(pair) and decision.get("stoploss_mode") == "tighten_only":
            agent_stop = decision.get("agent_stoploss")
            return None if agent_stop is None else float(agent_stop)
        return None

    def custom_roi(self, pair: str, trade, current_time, trade_duration: int, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        if self.shadow_mode or not self.enabled_callbacks.get("roi", False):
            self._log_shadow_event("roi", pair, {"trade_duration": trade_duration, "decision": decision})
            return None
        if self._agent_enabled_for_pair(pair):
            target_rr = decision.get("target_rr")
            return None if target_rr is None else float(target_rr)
        return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, current_time, entry_tag, side: str, **kwargs) -> bool:
        decision = self._pair_decision(pair)
        if self.shadow_mode or not self.enabled_callbacks.get("entry_confirm", False):
            self._log_shadow_event("entry_confirm", pair, {"amount": amount, "rate": rate, "decision": decision})
            return True
        if self._agent_enabled_for_pair(pair):
            return bool(decision.get("entry_allowed", True))
        return True
