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
        return self._overlay.get("enabled_callbacks", {"stake": True, "exit": False, "stoploss": False, "roi": False, "entry_confirm": False})

    def _pair_decision(self, pair: str) -> dict[str, Any]:
        return self._cache.get("pairs", {}).get(pair.upper(), {})

    def _agent_enabled_for_pair(self, pair: str) -> bool:
        decision = self._pair_decision(pair)
        return bool(decision) and bool(decision.get("agent_enabled", False)) and decision.get("governance_gate") == "passed"

    def bot_loop_start(self, current_time, **kwargs):
        self._refresh()
        parent = getattr(super(), "bot_loop_start", None)
        return parent(current_time, **kwargs) if callable(parent) else None

    def custom_exit(self, pair: str, trade, current_time, current_rate: float, current_profit: float, **kwargs):
        decision = self._pair_decision(pair)
        min_profit = float(self._overlay.get("exit_min_profit_threshold", -0.02))
        audit_payload = {"pair": pair, "mode": "shadow" if self.shadow_mode else "live", "current_profit": current_profit, "min_profit_threshold": min_profit, "decision": decision}
        self.audit.append_event("exit_shadow_trace.jsonl", audit_payload)

        if self.shadow_mode or not self.enabled_callbacks.get("exit", False):
            return None

        if not self._agent_enabled_for_pair(pair):
            return None

        if current_profit < min_profit and not bool(decision.get("force_exit_on_loss", False)):
            self.audit.append_event("exit_skip_trace.jsonl", {**audit_payload, "reason": "profit_below_threshold"})
            return None

        if bool(decision.get("exit_signal", False)):
            reason = decision.get("exit_reason", "agent_exit_signal")
            self.audit.append_event("exit_apply_trace.jsonl", {**audit_payload, "reason": reason})
            return reason
        return None
