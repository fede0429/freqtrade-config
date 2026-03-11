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
        return self._overlay.get("enabled_callbacks", {"stake": True, "exit": True, "stoploss": True, "roi": False, "entry_confirm": False})

    def _pair_decision(self, pair: str) -> dict[str, Any]:
        return self._cache.get("pairs", {}).get(pair.upper(), {})

    def _agent_enabled_for_pair(self, pair: str) -> bool:
        d = self._pair_decision(pair)
        return bool(d) and bool(d.get("agent_enabled", False)) and d.get("governance_gate") == "passed"

    def bot_loop_start(self, current_time, **kwargs):
        self._refresh()
        parent = getattr(super(), "bot_loop_start", None)
        return parent(current_time, **kwargs) if callable(parent) else None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, current_time, entry_tag, side: str, **kwargs) -> bool:
        decision = self._pair_decision(pair)
        audit_payload = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "amount": amount,
            "rate": rate,
            "entry_tag": entry_tag,
            "decision": decision,
        }
        self.audit.append_event("entry_confirm_trace.jsonl", audit_payload)

        if self.shadow_mode or not self.enabled_callbacks.get("entry_confirm", False):
            return True

        if not self._agent_enabled_for_pair(pair):
            self.audit.append_event("entry_confirm_skip_trace.jsonl", {**audit_payload, "reason": "agent_not_enabled"})
            return True

        confidence = float(decision.get("confidence", 0.0))
        min_conf = float(self._overlay.get("entry_min_confidence", 0.75))
        if confidence < min_conf:
            self.audit.append_event("entry_confirm_block_trace.jsonl", {**audit_payload, "reason": "confidence_below_threshold", "confidence": confidence})
            return False

        if not bool(decision.get("entry_allowed", True)):
            self.audit.append_event("entry_confirm_block_trace.jsonl", {**audit_payload, "reason": "entry_allowed_false"})
            return False

        self.audit.append_event("entry_confirm_apply_trace.jsonl", {**audit_payload, "applied": True})
        return True
