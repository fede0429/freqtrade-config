from __future__ import annotations
from typing import Any

from user_data.strategies.bridge_loader import BridgeLoader
from user_data.strategies.shadow_audit_writer import ShadowAuditWriter

# TODO:
# 把下面一行替换成你仓库里真实正在运行的主策略
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
    '''
    v2 目标：
    1. 正式走“继承真实主策略”路线
    2. 增加 shadow 对账能力
    3. 允许只放开 stake live
    4. 其余 callback 继续保守
    '''
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

    def _refresh(self) -> None:
        self._overlay = self.loader.load_overlay()
        self._cache = self.loader.load_decision_cache()

    @property
    def shadow_mode(self) -> bool:
        return bool(self._overlay.get("shadow_mode", True))

    @property
    def enabled_callbacks(self) -> dict[str, bool]:
        return self._overlay.get(
            "enabled_callbacks",
            {"stake": False, "exit": False, "stoploss": False, "roi": False, "entry_confirm": False},
        )

    def _pair_decision(self, pair: str) -> dict[str, Any]:
        return self._cache.get("pairs", {}).get(pair.upper(), {})

    def _agent_enabled_for_pair(self, pair: str) -> bool:
        decision = self._pair_decision(pair)
        if not decision:
            return False
        if decision.get("governance_gate") != "passed":
            return False
        return bool(decision.get("agent_enabled", False))

    def bot_loop_start(self, current_time, **kwargs):
        self._refresh()
        parent = getattr(super(), "bot_loop_start", None)
        if callable(parent):
            return parent(current_time, **kwargs)
        return None

    def custom_stake_amount(self, pair: str, current_time, current_rate: float, proposed_stake: float, min_stake, max_stake: float, leverage: float, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        self.audit.append_event(
            "stake_decision_trace.jsonl",
            {"pair": pair, "mode": "shadow" if self.shadow_mode else "live", "proposed_stake": proposed_stake, "decision": decision},
        )

        if self.shadow_mode or not self.enabled_callbacks.get("stake", False):
            return proposed_stake

        if not self._agent_enabled_for_pair(pair):
            return proposed_stake

        confidence = float(decision.get("confidence", 0.0))
        min_conf = float(self._overlay.get("min_confidence_for_live", 0.70))
        if confidence < min_conf:
            return proposed_stake

        multiplier = float(decision.get("stake_multiplier", 1.0))
        max_mult = float(self._overlay.get("max_stake_multiplier", 1.50))
        multiplier = min(multiplier, max_mult)

        stake = proposed_stake * multiplier
        if max_stake:
            stake = min(stake, max_stake)

        self.audit.append_event(
            "stake_apply_trace.jsonl",
            {"pair": pair, "applied": True, "confidence": confidence, "multiplier": multiplier, "final_stake": stake},
        )
        return max(stake, 0.0)

    def custom_exit(self, pair: str, trade, current_time, current_rate: float, current_profit: float, **kwargs):
        decision = self._pair_decision(pair)
        self.audit.append_event(
            "exit_shadow_trace.jsonl",
            {"pair": pair, "mode": "shadow" if self.shadow_mode else "live", "current_profit": current_profit, "decision": decision},
        )
        if self.shadow_mode or not self.enabled_callbacks.get("exit", False):
            return None
        if self._agent_enabled_for_pair(pair) and bool(decision.get("exit_signal", False)):
            return decision.get("exit_reason", "agent_exit_signal")
        return None

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float, current_profit: float, after_fill: bool, **kwargs):
        decision = self._pair_decision(pair)
        self.audit.append_event(
            "stoploss_shadow_trace.jsonl",
            {"pair": pair, "mode": "shadow" if self.shadow_mode else "live", "current_profit": current_profit, "decision": decision},
        )
        if self.shadow_mode or not self.enabled_callbacks.get("stoploss", False):
            return None
        if self._agent_enabled_for_pair(pair) and decision.get("stoploss_mode") == "tighten_only":
            agent_stop = decision.get("agent_stoploss")
            return None if agent_stop is None else float(agent_stop)
        return None

    def custom_roi(self, pair: str, trade, current_time, trade_duration: int, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        self.audit.append_event(
            "roi_shadow_trace.jsonl",
            {"pair": pair, "mode": "shadow" if self.shadow_mode else "live", "trade_duration": trade_duration, "decision": decision},
        )
        if self.shadow_mode or not self.enabled_callbacks.get("roi", False):
            return None
        if self._agent_enabled_for_pair(pair):
            target_rr = decision.get("target_rr")
            return None if target_rr is None else float(target_rr)
        return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, current_time, entry_tag, side: str, **kwargs) -> bool:
        decision = self._pair_decision(pair)
        self.audit.append_event(
            "entry_confirm_trace.jsonl",
            {"pair": pair, "mode": "shadow" if self.shadow_mode else "live", "amount": amount, "rate": rate, "decision": decision},
        )
        if self.shadow_mode or not self.enabled_callbacks.get("entry_confirm", False):
            return True
        if self._agent_enabled_for_pair(pair):
            return bool(decision.get("entry_allowed", True))
        return True
