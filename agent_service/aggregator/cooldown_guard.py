from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
from typing import Dict, Any


def utc_now():
    return datetime.now(timezone.utc)


class CooldownGuard:
    def __init__(self, config: Dict[str, Any], state_path: str = "agent_service/reports/cooldown_state.json") -> None:
        self.config = config or {}
        self.state_path = Path(state_path)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if not self.state_path.exists():
            return {"pairs": {}}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {"pairs": {}}

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")

    def global_defaults(self) -> Dict[str, Any]:
        return self.config.get(
            "global_defaults",
            {
                "cooldown_minutes_on_blocking_anomaly": 45,
                "cooldown_minutes_on_provider_gate_fail": 20,
                "cooldown_entry_block": True,
                "cooldown_stake_multiplier_cap": 1.0,
            },
        )

    def pair_overrides(self) -> Dict[str, Any]:
        raw = self.config.get("pair_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}

    def config_for_pair(self, pair: str) -> Dict[str, Any]:
        cfg = dict(self.global_defaults())
        cfg.update(self.pair_overrides().get(pair.upper(), {}))
        return cfg

    def _pair_state(self, pair: str) -> dict:
        pairs = self.state.setdefault("pairs", {})
        return pairs.setdefault(pair.upper(), {})

    def active_cooldown(self, pair: str) -> dict:
        st = self._pair_state(pair)
        until = st.get("cooldown_until")
        reason = st.get("reason")
        if not until:
            return {"active": False, "reason": None, "cooldown_until": None}
        try:
            until_dt = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
        except Exception:
            return {"active": False, "reason": None, "cooldown_until": None}
        active = utc_now() < until_dt
        if not active:
            st["cooldown_until"] = None
            st["reason"] = None
            self._save_state()
        return {"active": active, "reason": reason if active else None, "cooldown_until": until if active else None}

    def maybe_enter_cooldown(self, pair: str, anomaly_blocking: bool, provider_gate_passed: bool) -> dict:
        cfg = self.config_for_pair(pair)
        minutes = None
        reason = None
        if anomaly_blocking:
            minutes = int(cfg.get("cooldown_minutes_on_blocking_anomaly", 45))
            reason = "blocking_anomaly"
        elif not provider_gate_passed:
            minutes = int(cfg.get("cooldown_minutes_on_provider_gate_fail", 20))
            reason = "provider_gate_fail"

        if minutes is None:
            return self.active_cooldown(pair)

        until = utc_now() + timedelta(minutes=minutes)
        st = self._pair_state(pair)
        st["cooldown_until"] = until.isoformat()
        st["reason"] = reason
        self._save_state()
        return {"active": True, "reason": reason, "cooldown_until": until.isoformat()}

    def apply_entry_policy(self, pair: str, entry_allowed: bool) -> bool:
        cfg = self.config_for_pair(pair)
        cd = self.active_cooldown(pair)
        if cd["active"] and bool(cfg.get("cooldown_entry_block", True)):
            return False
        return entry_allowed

    def apply_stake_multiplier_cap(self, pair: str, stake_multiplier: float) -> float:
        cfg = self.config_for_pair(pair)
        cd = self.active_cooldown(pair)
        if cd["active"]:
            return min(float(stake_multiplier), float(cfg.get("cooldown_stake_multiplier_cap", 1.0)))
        return float(stake_multiplier)
