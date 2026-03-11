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
    use_custom_roi = True
    use_exit_signal = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loader = BridgeLoader(self.agent_overlay_path, self.decision_cache_path)
        self.audit = ShadowAuditWriter()
        self._overlay: dict[str, Any] = {}
        self._cache: dict[str, Any] = {}
        self._refresh()

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _normalize_time(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _refresh(self) -> None:
        self._overlay = self.loader.load_overlay()
        self._cache = self.loader.load_decision_cache()

    def _runmode_name(self) -> str:
        runmode = None
        config = getattr(self, "config", None)
        if isinstance(config, dict):
            runmode = config.get("runmode")
        if runmode is None:
            dataprov = getattr(self, "dp", None)
            runmode = getattr(dataprov, "runmode", None)
        if runmode is None:
            return ""
        return str(getattr(runmode, "value", runmode)).lower()

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

    def _cache_is_fresh(self, reference_time: datetime | None = None) -> bool:
        if (
            self._runmode_name() in {"backtest", "hyperopt"}
            and not bool(self._overlay.get("enforce_cache_ttl_in_backtest", False))
        ):
            return True

        ttl = int(self._overlay.get("cache_ttl_seconds", 90))
        max_future_skew = int(self._overlay.get("max_future_skew_seconds", 5))
        if ttl <= 0:
            return True

        ts = self._cache.get("ts")
        if not ts:
            return False

        try:
            cache_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            compare_time = self._normalize_time(reference_time) or self._utc_now()
            age = (compare_time - cache_ts).total_seconds()
            return -max_future_skew <= age <= ttl
        except Exception:
            return False

    def _agent_enabled_for_pair(self, pair: str, current_time: datetime | None = None) -> bool:
        decision = self._pair_decision(pair)
        if not decision:
            return False
        if not self._pair_allowed(pair):
            return False
        if not self._cache_is_fresh(current_time):
            return False
        if decision.get("governance_gate") != "passed":
            return False
        return bool(decision.get("agent_enabled", False))

    def _trace(self, filename: str, payload: dict[str, Any]) -> None:
        self.audit.append_event(filename, payload)

    def _call_parent(self, method_name: str, *args, **kwargs):
        parent = getattr(super(), method_name, None)
        return parent(*args, **kwargs) if callable(parent) else None

    def _as_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _resolve_agent_roi(self, decision: dict[str, Any]) -> tuple[float | None, str]:
        direct_ratio = self._as_float(decision.get("target_profit_ratio"))
        if direct_ratio is not None:
            return max(direct_ratio, 0.0), "target_profit_ratio"

        target_rr = self._as_float(decision.get("target_rr"))
        if target_rr is None:
            return None, "missing_target_rr"

        stop_reference = self._as_float(decision.get("agent_stoploss"))
        stop_source = "agent_stoploss"
        if stop_reference is None:
            stop_reference = self._as_float(getattr(self, "stoploss", None))
            stop_source = "strategy_stoploss"
        if stop_reference is None:
            return None, "missing_stop_reference"

        roi_value = abs(stop_reference) * target_rr
        max_ratio = self._as_float(self._overlay.get("max_target_profit_ratio"))
        if max_ratio is not None:
            roi_value = min(roi_value, max_ratio)
        return max(roi_value, 0.0), f"derived_from_{stop_source}_x_target_rr"

    def bot_loop_start(self, current_time, **kwargs):
        self._refresh()
        self._trace(
            "bridge_runtime_trace.jsonl",
            {
                "shadow_mode": self.shadow_mode,
                "enabled_callbacks": self.enabled_callbacks,
                "cache_fresh": self._cache_is_fresh(current_time),
                "runmode": self._runmode_name(),
                "pair_count": len(self._cache.get("pairs", {})),
            },
        )
        return self._call_parent("bot_loop_start", current_time, **kwargs)

    def custom_stake_amount(self, pair: str, current_time, current_rate: float, proposed_stake: float, min_stake, max_stake: float, leverage: float, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "proposed_stake": proposed_stake,
            "decision": decision,
            "cache_fresh": self._cache_is_fresh(current_time),
            "pair_allowed": self._pair_allowed(pair),
        }
        self._trace("stake_decision_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("stake", False):
            self._trace("stake_fallback_trace.jsonl", {**base, "reason": "shadow_or_disabled"})
            return proposed_stake
        if not self._agent_enabled_for_pair(pair, current_time):
            self._trace("stake_fallback_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return proposed_stake

        confidence = float(decision.get("confidence", 0.0))
        min_conf = float(self._overlay.get("min_confidence_for_live", 0.72))
        if confidence < min_conf:
            self._trace(
                "stake_fallback_trace.jsonl",
                {**base, "reason": "confidence_below_threshold", "confidence": confidence},
            )
            return proposed_stake

        multiplier = min(
            float(decision.get("stake_multiplier", 1.0)),
            float(self._overlay.get("max_stake_multiplier", 1.50)),
        )
        stake = proposed_stake * multiplier
        if max_stake:
            stake = min(stake, max_stake)
        if min_stake:
            stake = max(stake, min_stake)

        self._trace(
            "stake_apply_trace.jsonl",
            {**base, "confidence": confidence, "multiplier": multiplier, "final_stake": stake},
        )
        return max(stake, 0.0)

    def custom_exit(self, pair: str, trade, current_time, current_rate: float, current_profit: float, **kwargs):
        parent_exit = self._call_parent(
            "custom_exit",
            pair,
            trade,
            current_time,
            current_rate,
            current_profit,
            **kwargs,
        )
        decision = self._pair_decision(pair)
        min_profit = float(self._overlay.get("exit_min_profit_threshold", -0.01))
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "current_profit": current_profit,
            "min_profit_threshold": min_profit,
            "decision": decision,
            "parent_exit": parent_exit,
        }
        self._trace("exit_shadow_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("exit", False):
            return parent_exit
        if not self._agent_enabled_for_pair(pair, current_time):
            self._trace("exit_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return parent_exit
        if current_profit < min_profit and not bool(decision.get("force_exit_on_loss", False)):
            self._trace("exit_skip_trace.jsonl", {**base, "reason": "profit_below_threshold"})
            return parent_exit
        if bool(decision.get("exit_signal", False)):
            reason = decision.get("exit_reason", "agent_exit_signal")
            self._trace("exit_apply_trace.jsonl", {**base, "reason": reason})
            return reason
        return parent_exit

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float, current_profit: float, after_fill: bool, **kwargs):
        parent_stoploss = self._call_parent(
            "custom_stoploss",
            pair,
            trade,
            current_time,
            current_rate,
            current_profit,
            after_fill,
            **kwargs,
        )
        decision = self._pair_decision(pair)
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "current_profit": current_profit,
            "decision": decision,
            "parent_stoploss": parent_stoploss,
        }
        self._trace("stoploss_shadow_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("stoploss", False):
            return parent_stoploss
        if not self._agent_enabled_for_pair(pair, current_time):
            self._trace("stoploss_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return parent_stoploss
        if decision.get("stoploss_mode") != "tighten_only":
            self._trace("stoploss_skip_trace.jsonl", {**base, "reason": "mode_not_tighten_only"})
            return parent_stoploss

        agent_stop = self._as_float(decision.get("agent_stoploss"))
        if agent_stop is None:
            self._trace("stoploss_skip_trace.jsonl", {**base, "reason": "missing_agent_stop"})
            return parent_stoploss

        parent_stop_value = self._as_float(parent_stoploss)
        applied_stop = agent_stop if parent_stop_value is None else max(parent_stop_value, agent_stop)
        self._trace(
            "stoploss_apply_trace.jsonl",
            {**base, "agent_stoploss": agent_stop, "applied_stoploss": applied_stop},
        )
        return applied_stop

    def custom_roi(self, pair: str, trade, current_time, trade_duration: int, entry_tag, side: str, **kwargs):
        decision = self._pair_decision(pair)
        min_duration = int(self._overlay.get("roi_min_trade_duration", 5))
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "trade_duration": trade_duration,
            "min_trade_duration": min_duration,
            "decision": decision,
        }
        self._trace("roi_shadow_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("roi", False):
            return None
        if not self._agent_enabled_for_pair(pair, current_time):
            self._trace("roi_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return None
        if trade_duration < min_duration:
            self._trace("roi_skip_trace.jsonl", {**base, "reason": "duration_below_threshold"})
            return None

        roi_value, roi_source = self._resolve_agent_roi(decision)
        if roi_value is None:
            self._trace("roi_skip_trace.jsonl", {**base, "reason": roi_source})
            return None

        self._trace("roi_apply_trace.jsonl", {**base, "roi_value": roi_value, "roi_source": roi_source})
        return roi_value

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str, current_time, entry_tag, side: str, **kwargs) -> bool:
        decision = self._pair_decision(pair)
        base = {
            "pair": pair,
            "mode": "shadow" if self.shadow_mode else "live",
            "amount": amount,
            "rate": rate,
            "entry_tag": entry_tag,
            "decision": decision,
        }
        self._trace("entry_confirm_trace.jsonl", base)

        if self.shadow_mode or not self.enabled_callbacks.get("entry_confirm", False):
            return True
        if not self._agent_enabled_for_pair(pair, current_time):
            self._trace("entry_confirm_skip_trace.jsonl", {**base, "reason": "agent_not_enabled"})
            return True

        confidence = float(decision.get("confidence", 0.0))
        min_conf = float(self._overlay.get("entry_min_confidence", 0.75))
        if confidence < min_conf:
            self._trace(
                "entry_confirm_block_trace.jsonl",
                {**base, "reason": "confidence_below_threshold", "confidence": confidence},
            )
            return False
        if not bool(decision.get("entry_allowed", True)):
            self._trace("entry_confirm_block_trace.jsonl", {**base, "reason": "entry_allowed_false"})
            return False

        self._trace("entry_confirm_apply_trace.jsonl", {**base, "applied": True})
        return True
