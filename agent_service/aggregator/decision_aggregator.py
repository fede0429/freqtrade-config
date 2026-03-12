import json
from pathlib import Path
from datetime import datetime, timezone

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

class DecisionAggregator:
    def __init__(self, cache_ttl_seconds=90, shadow_mode=True):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.shadow_mode = shadow_mode

    def build_pair_decision(self, pair, snapshots):
        provider_count = len(snapshots)
        confidence = round(sum(float(getattr(s, "score", 0.0)) for s in snapshots) / provider_count, 4) if provider_count else 0.0
        providers = {}
        news_governance_triggered = []
        governance_gate = "passed"
        trading_mode = "paper_candidate"
        agent_enabled = provider_count > 0
        for s in snapshots:
            providers[getattr(s, "provider")] = {
                "status": getattr(s, "status"),
                "score": getattr(s, "score"),
                "ts": getattr(s, "ts"),
                "stale": getattr(s, "stale"),
                "raw_ref": getattr(s, "raw_ref", {}),
            }
            raw_ref = getattr(s, "raw_ref", {}) or {}
            event_type = raw_ref.get("event_type") or raw_ref.get("signals", {}).get("event_type")
            source_tier = raw_ref.get("source_tier") or raw_ref.get("signals", {}).get("source_tier")
            cred = raw_ref.get("credibility_score") or raw_ref.get("signals", {}).get("credibility_score")
            if event_type in {"exchange_incident", "regulatory_action"}:
                news_governance_triggered.append({"provider": getattr(s, "provider"), "event_type": event_type, "source_tier": source_tier, "credibility_score": cred})
            if event_type == "exchange_incident":
                governance_gate = "blocked"
                trading_mode = "review_shadow"
                agent_enabled = False

        return {
            "agent_enabled": agent_enabled,
            "pair_enabled": True,
            "governance_gate": governance_gate,
            "trading_mode": trading_mode,
            "rollout_state": "paper" if governance_gate == "passed" else "shadow",
            "confidence": confidence,
            "risk_score": 0.0,
            "providers": providers,
            "entry": {"entry_allowed": confidence >= 0.75 and governance_gate == "passed", "entry_reason": "snapshot_alignment" if governance_gate == "passed" else "news_governance_blocked", "entry_min_confidence": 0.75},
            "stake": {"stake_multiplier": 1.15 if confidence >= 0.75 and governance_gate == "passed" else 1.0, "stake_cap_ratio": 0.12},
            "exit": {"exit_signal": False, "exit_reason": None, "force_exit_on_loss": False},
            "stoploss": {"stoploss_mode": "tighten_only", "agent_stoploss": -0.045},
            "roi": {"target_rr": 1.8, "roi_min_trade_duration": 5},
            "trace": {"evidence_refs": [f"{getattr(s, 'provider')}:{pair}" for s in snapshots]},
            "news_governance": {"triggered_events": news_governance_triggered, "block": governance_gate == "blocked", "review": trading_mode == "review_shadow", "escalate": any(e["event_type"] in {"exchange_incident", "regulatory_action"} for e in news_governance_triggered)},
            "entry_allowed": confidence >= 0.75 and governance_gate == "passed",
            "stake_multiplier": 1.15 if confidence >= 0.75 and governance_gate == "passed" else 1.0,
            "exit_signal": False,
            "exit_reason": None,
            "stoploss_mode": "tighten_only",
            "agent_stoploss": -0.045,
            "target_rr": 1.8,
        }

    def build_decision_cache(self, pair_snapshots):
        return {"schema_version": "2.0", "ts": utc_now_iso(), "source": "decision_aggregator", "env": "dry-run", "global": {"shadow_mode": self.shadow_mode, "governance_gate": "passed", "cache_ttl_seconds": self.cache_ttl_seconds, "aggregator_health": "ok", "fallback_mode": "base_strategy_only"}, "pairs": {pair: self.build_pair_decision(pair, snaps) for pair, snaps in pair_snapshots.items()}}

    def write_decision_cache(self, pair_snapshots, output_path="user_data/agent_runtime/state/decision_cache.json"):
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.build_decision_cache(pair_snapshots), indent=2, ensure_ascii=False), encoding="utf-8")
        return out
