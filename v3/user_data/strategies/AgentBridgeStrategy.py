from __future__ import annotations
from datetime import datetime, timezone
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

    def _refresh(self) -> None:
        self._overlay = self.loader.load_overlay()
        self._cache = self.loader.load_decision_cache()

    def _utc_now(self):
        return datetime.now(timezone.utc)

    @property
    def shadow_mode(self) -> bool:
        return bool(self._overlay.get("shadow_mode", True))

    @property
    def enabled_callbacks(self) -> dict[str, bool]:
        return self._overlay.get("enabled_callbacks", {"stake": False, "exit": False, "stoploss": False, "roi": False, "entry_confirm": False})

    def _pair_decision(self, pair: str) -> dict[str, Any]:
        return self._cache.get("pairs", {}).get(pair.upper(), {})

    def _pair_allowed(self, pair: str) -> bool:
        allowed = [p.upper() for p in self._overlay.get("enabled_pairs", [])]
        return not allowed or pair.upper() in allowed

    def _cache_is_fresh(self) -> bool:
        ts = self._cache.get("ts")
        ttl = int(self._overlay.get("cache_ttl_seconds", 90))
        if not ts:
            return False
        try:
            cache_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = (self._utc_now() - cache_ts).total_seconds()
            return age <= ttl
        except Exception:
            return False

    def _agent_enabled_for_pair(self, pair: str) -> bool:
        decision = self._pair_decision(pair)
        if not decision or not self._pair_allowed(pair) or not self._cache_is_fresh():
            return False
        if decision.get("governance_gate") != "passed":
            return False
        return bool(decision.get("agent_enabled", False))

    def bot_loop_start(self, current_time, **kwargs):
        self._refresh()
        parent = getattr(super(), "bot_loop_start", None)
        return parent(current_time, **kwargs) if callable(parent) else None

    def custom_stake_amount(self, pair: str, current_time, current_rate: float, proposed_stake: float, min_stake, max_stake: float, leverage: float, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        audit_base = {"pair": pair, "mode": "shadow" if self.shadow_mode else "live", "proposed_stake": proposed_stake, "decision": decision, "cache_fresh": self._cache_is_fresh(), "pair_allowed": self._pair_allowed(pair)}
        self.audit.append_event("stake_decision_trace.jsonl", audit_base)

        if self.shadow_mode or not self.enabled_callbacks.get("stake", False):
            self.audit.append_event("stake_fallback_trace.jsonl", {**audit_base, "reason": "shadow_or_disabled"})
            return proposed_stake

        if not self._agent_enabled_for_pair(pair):
            self.audit.append_event("stake_fallback_trace.jsonl", {**audit_base, "reason": "agent_not_enabled"})
            return proposed_stake

        confidence = float(decision.get("confidence", 0.0))
        min_conf = float(self._overlay.get("min_confidence_for_live", 0.70))
        if confidence < min_conf:
            self.audit.append_event("stake_fallback_trace.jsonl", {**audit_base, "reason": "confidence_below_threshold", "confidence": confidence})
            return proposed_stake

        multiplier = float(decision.get("stake_multiplier", 1.0))
        max_mult = float(self._overlay.get("max_stake_multiplier", 1.50))
        multiplier = min(multiplier, max_mult)

        stake = proposed_stake * multiplier
        if max_stake:
            stake = min(stake, max_stake)
        if min_stake:
            stake = max(stake, min_stake)

        self.audit.append_event("stake_apply_trace.jsonl", {"pair": pair, "confidence": confidence, "multiplier": multiplier, "final_stake": stake, "governance_gate": decision.get("governance_gate")})
        return max(stake, 0.0)
