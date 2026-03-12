import json
from pathlib import Path

INPUTS = {
    "runtime_readiness":"agent_service/reports/runtime_readiness_report.json",
    "live_compare":"agent_service/reports/live_calibration_compare_report.json",
    "pair_drift":"agent_service/reports/pair_drift_summary.json",
    "daily_ops":"agent_service/reports/daily_ops_summary.json",
    "weekly_ops":"agent_service/reports/weekly_ops_summary.json",
    "decision_cache":"user_data/agent_runtime/state/decision_cache.json",
}

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def classify_pair(meta, drift):
    governance = meta.get("governance_gate")
    trading_mode = meta.get("trading_mode")
    confidence = float(meta.get("confidence", 0.0))
    news_governance = meta.get("news_governance", {}) or {}
    blocked = governance != "passed"
    review = bool(news_governance.get("review", False)) or trading_mode == "review_shadow"
    escalate = bool(news_governance.get("escalate", False))
    drifted = bool(drift.get("governance_changed")) or bool(drift.get("trading_mode_changed")) or bool(drift.get("entry_changed"))
    action = "hold"; reasons = []
    if blocked: action = "hold"; reasons.append("governance_blocked")
    elif review: action = "review"; reasons.append("review_shadow_or_news_review")
    elif drifted: action = "hold"; reasons.append("pair_drift_detected")
    elif confidence >= 0.80: action = "promote_candidate"; reasons.append("high_confidence_stable_pair")
    elif confidence >= 0.75: action = "watch_candidate"; reasons.append("mid_confidence_pair")
    else: action = "hold"; reasons.append("confidence_below_threshold")
    if escalate: reasons.append("news_escalation_present")
    return {"action": action, "reasons": reasons, "confidence": confidence, "governance_gate": governance, "trading_mode": trading_mode, "news_governance": news_governance, "drift": drift}

def main():
    readiness = load_json(INPUTS["runtime_readiness"], {})
    compare = load_json(INPUTS["live_compare"], {})
    drift = load_json(INPUTS["pair_drift"], {"pairs": {}})
    daily = load_json(INPUTS["daily_ops"], {})
    weekly = load_json(INPUTS["weekly_ops"], {})
    decision_cache = load_json(INPUTS["decision_cache"], {"pairs": {}})
    pairs = {}; promote_candidates=[]; hold_pairs=[]; review_pairs=[]
    for pair, meta in decision_cache.get("pairs", {}).items():
        row = classify_pair(meta, drift.get("pairs", {}).get(pair, {}))
        pairs[pair] = row
        if row["action"] == "promote_candidate": promote_candidates.append({"pair": pair, **row})
        elif row["action"] == "review": review_pairs.append({"pair": pair, **row})
        else: hold_pairs.append({"pair": pair, **row})
    payload = {"kind":"promote_hold_decision_panel","runtime_readiness_status": readiness.get("overall_status"), "compare_available": bool(compare), "daily_ops_status": daily.get("runtime_readiness_status"), "weekly_total_runs": weekly.get("total_runs"), "pairs": pairs, "promote_candidates": promote_candidates, "review_pairs": review_pairs, "hold_pairs": hold_pairs, "summary": {"promote_candidate_count": len(promote_candidates), "review_count": len(review_pairs), "hold_count": len(hold_pairs)}}
    out = Path("agent_service/reports/promote_hold_decision_panel.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
