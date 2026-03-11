from __future__ import annotations
from typing import Any

from user_data.strategies.bridge_loader import BridgeLoader
from user_data.strategies.shadow_audit_writer import ShadowAuditWriter

# TODO:
# from user_data.strategies.MyLiveStrategy import MyLiveStrategy as BaseStrategy
try:
    from user_data.strategies.SampleStrategy import SampleStrategy as BaseStrategy
except Exception:
    class BaseStrategy:
        timeframe = "5m"
        stoploss = -0.10
        process_only_new_candles = True
        use_custom_stoploss = True
        use_exit_signal = True
        def bot_loop_start(self, current_time, **kwargs): return None
        def custom_stake_amount(self, *args, **kwargs): return kwargs.get("proposed_stake")
        def custom_exit(self, *args, **kwargs): return None
        def custom_stoploss(self, *args, **kwargs): return None
        def custom_roi(self, *args, **kwargs): return None
        def confirm_trade_entry(self, *args, **kwargs): return True

class AgentBridgeStrategy(BaseStrategy):
    agent_overlay_path = "user_data/config/agent_overlay.json"
    decision_cache_path = "user_data/agent_runtime/state/decision_cache.json"
    use_custom_stoploss = True
    use_exit_signal = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loader = BridgeLoader(self.agent_overlay_path, self.decision_cache_path)
        self.audit = ShadowAuditWriter()
        self._overlay = self.loader.load_overlay()
        self._cache = self.loader.load_decision_cache()

    def _refresh(self):
        self._overlay = self.loader.load_overlay()
        self._cache = self.loader.load_decision_cache()

    @property
    def shadow_mode(self) -> bool:
        return bool(self._overlay.get("shadow_mode", True))

    @property
    def enabled_callbacks(self) -> dict[str, bool]:
        return self._overlay.get("enabled_callbacks", {"stake": True, "exit": True, "stoploss": True, "roi": False, "entry_confirm": True})

    def _pair_decision(self, pair: str) -> dict[str, Any]:
        return self._cache.get("pairs", {}).get(pair.upper(), {})

    def _agent_enabled_for_pair(self, pair: str) -> bool:
        d = self._pair_decision(pair)
        return bool(d) and bool(d.get("agent_enabled", False)) and d.get("governance_gate") == "passed"

    def bot_loop_start(self, current_time, **kwargs):
        self._refresh()
        parent = getattr(super(), "bot_loop_start", None)
        return parent(current_time, **kwargs) if callable(parent) else None

    def custom_roi(self, pair: str, trade, current_time, trade_duration: int, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        min_duration = int(self._overlay.get("roi_min_trade_duration", 5))
        audit_payload = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "trade_duration": trade_duration,
            "min_trade_duration": min_duration,
            "decision": decision,
        }
        self.audit.append_event("roi_shadow_trace.jsonl", audit_payload)

        if self.shadow_mode or not self.enabled_callbacks.get("roi", False):
            return None

        if not self._agent_enabled_for_pair(pair):
            self.audit.append_event("roi_skip_trace.jsonl", {**audit_payload, "reason": "agent_not_enabled"})
            return None

        if trade_duration < min_duration:
            self.audit.append_event("roi_skip_trace.jsonl", {**audit_payload, "reason": "duration_below_threshold"})
            return None

        target_rr = decision.get("target_rr")
        if target_rr is None:
            self.audit.append_event("roi_skip_trace.jsonl", {**audit_payload, "reason": "missing_target_rr"})
            return None

        roi_value = float(target_rr)
        self.audit.append_event("roi_apply_trace.jsonl", {**audit_payload, "roi_value": roi_value})
        return roi_value
