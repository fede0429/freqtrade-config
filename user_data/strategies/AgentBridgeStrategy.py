from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from user_data.strategies.bridge_loader import BridgeLoader
from user_data.strategies.shadow_audit_writer import ShadowAuditWriter

from user_data.strategies.AdaptiveMetaStrategy import AdaptiveMetaStrategy as BaseStrategy



class AgentBridgeStrategy(BaseStrategy):
    agent_overlay_path = "user_data/config/agent_overlay.json"
    decision_cache_path = "user_data/agent_runtime/state/decision_cache.json"
    use_custom_stoploss = True
    use_exit_signal = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loader = BridgeLoader(self.agent_overlay_path, self.decision_cache_path)
        self.audit = ShadowAuditWriter()
        self._overlay: dict[str, Any] = {}
        self._cache: dict[str, Any] = {}
        self._refresh()

    def _utc_now(self):
        return datetime.now(timezone.utc)

    def _refresh(self):
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
        d = self._pair_decision(pair)
        if not d:
            return False
        if not self._pair_allowed(pair):
            return False
        if not self._cache_is_fresh():
            return False
        if d.get("governance_gate") != "passed":
            return False
        return bool(d.get("agent_enabled", False))

    def _trace(self, filename: str, payload: dict[str, Any]) -> None:
        self.audit.append_event(filename, payload)

    def bot_loop_start(self, current_time, **kwargs):
        self._refresh()
        self._trace("bridge_runtime_trace.jsonl", {
            "shadow_mode": self.shadow_mode,
            "enabled_callbacks": self.enabled_callbacks,
            "cache_fresh": self._cache_is_fresh(),
            "pair_count": len(self._cache.get("pairs", {})),
        })
        parent = getattr(super(), "bot_loop_start", None)
        return parent(current_time, **kwargs) if callable(parent) else None

    def custom_stake_amount(self, pair: str, current_time, current_rate: float, proposed_stake: float, min_stake, max_stake: float, leverage: float, entry_tag, side: str, **kwargs):
        d = self._pair_decision(pair)
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "proposed_stake": proposed_stake,
            "decision": d,
            "cache_fresh": self._cache_is_fresh(),
            "pair_allowed": self._pair_allowed(pair),
        }
        self._trace("stake_decision_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("stake", False):
            self._trace("stake_fallback_trace.jsonl", {**base, "reason": "shadow_or_disabled"})
            return proposed_stake
        if not self._agent_enabled_for_pair(pair):
            self._trace("stake_fallback_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return proposed_stake

        confidence = float(d.get("confidence", 0.0))
        min_conf = float(self._overlay.get("min_confidence_for_live", 0.72))
        if confidence < min_conf:
            self._trace("stake_fallback_trace.jsonl", {**base, "reason": "confidence_below_threshold", "confidence": confidence})
            return proposed_stake

        multiplier = min(float(d.get("stake_multiplier", 1.0)), float(self._overlay.get("max_stake_multiplier", 1.50)))
        stake = proposed_stake * multiplier
        if max_stake:
            stake = min(stake, max_stake)
        if min_stake:
            stake = max(stake, min_stake)

        self._trace("stake_apply_trace.jsonl", {**base, "confidence": confidence, "multiplier": multiplier, "final_stake": stake})
        return max(stake, 0.0)

    def custom_exit(self, pair: str, trade, current_time, current_rate: float, current_profit: float, **kwargs):
        d = self._pair_decision(pair)
        min_profit = float(self._overlay.get("exit_min_profit_threshold", -0.01))
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "current_profit": current_profit,
            "min_profit_threshold": min_profit,
            "decision": d,
        }
        self._trace("exit_shadow_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("exit", False):
            return None
        if not self._agent_enabled_for_pair(pair):
            self._trace("exit_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return None
        if current_profit < min_profit and not bool(d.get("force_exit_on_loss", False)):
            self._trace("exit_skip_trace.jsonl", {**base, "reason": "profit_below_threshold"})
            return None
        if bool(d.get("exit_signal", False)):
            reason = d.get("exit_reason", "agent_exit_signal")
            self._trace("exit_apply_trace.jsonl", {**base, "reason": reason})
            return reason
        return None

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float, current_profit: float, after_fill: bool, **kwargs):
        d = self._pair_decision(pair)
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "current_profit": current_profit,
            "decision": d,
        }
        self._trace("stoploss_shadow_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("stoploss", False):
            return None
        if not self._agent_enabled_for_pair(pair):
            self._trace("stoploss_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return None
        if d.get("stoploss_mode") != "tighten_only":
            self._trace("stoploss_skip_trace.jsonl", {**base, "reason": "mode_not_tighten_only"})
            return None
        agent_stop = d.get("agent_stoploss")
        if agent_stop is None:
            self._trace("stoploss_skip_trace.jsonl", {**base, "reason": "missing_agent_stop"})
            return None
        self._trace("stoploss_apply_trace.jsonl", {**base, "applied_stoploss": float(agent_stop)})
        return float(agent_stop)

    def custom_roi(self, pair: str, trade, current_time, trade_duration: int, entry_tag, side: str, **kwargs):
        d = self._pair_decision(pair)
        min_duration = int(self._overlay.get("roi_min_trade_duration", 5))
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "trade_duration": trade_duration,
            "min_trade_duration": min_duration,
            "decision": d,
        }
        self._trace("roi_shadow_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("roi", False):
            return None
        if not self._agent_enabled_for_pair(pair):
            self._trace("roi_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return None
        if trade_duration < min_duration:
            self._trace("roi_skip_trace.jsonl", {**base, "reason": "duration_below_threshold"})
            return None
        target_rr = d.get("target_rr")
        if target_rr is None:
            self._trace("roi_skip_trace.jsonl", {**base, "reason": "missing_target_rr"})
            return None
        roi_value = float(target_rr)
        self._trace("roi_apply_trace.jsonl", {**base, "roi_value": roi_value})
        return roi_value

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, current_time, entry_tag, side: str, **kwargs) -> bool:
        d = self._pair_decision(pair)
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "amount": amount,
            "rate": rate,
            "entry_tag": entry_tag,
            "decision": d,
        }
        self._trace("entry_confirm_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("entry_confirm", False):
            return True
        if not self._agent_enabled_for_pair(pair):
            self._trace("entry_confirm_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return True
        confidence = float(d.get("confidence", 0.0))
        min_conf = float(self._overlay.get("entry_min_confidence", 0.75))
        if confidence < min_conf:
            self._trace("entry_confirm_block_trace.jsonl", {**base, "reason": "confidence_below_threshold", "confidence": confidence})
            return False
        if not bool(d.get("entry_allowed", True)):
            self._trace("entry_confirm_block_trace.jsonl", {**base, "reason": "entry_allowed_false"})
            return False
        self._trace("entry_confirm_apply_trace.jsonl", {**base, "applied": True})
        return True
