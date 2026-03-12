import json
from pathlib import Path

INPUTS = {"shadow_run_summary":"agent_service/reports/shadow_run_summary.json","runtime_readiness":"agent_service/reports/runtime_readiness_report.json","live_compare":"agent_service/reports/live_calibration_compare_report.json","pair_drift":"agent_service/reports/pair_drift_summary.json"}

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    shadow = load_json(INPUTS["shadow_run_summary"], {})
    readiness = load_json(INPUTS["runtime_readiness"], {})
    compare = load_json(INPUTS["live_compare"], {})
    drift = load_json(INPUTS["pair_drift"], {"pairs": {}})
    payload = {"kind":"daily_ops_summary","shadow_run_status": shadow.get("status"), "shadow_failed_steps": shadow.get("failed_steps", []), "runtime_readiness_status": readiness.get("overall_status"), "compare_available": bool(compare), "top_candidate_count": len(compare.get("candidate_ranking", {}).get("top_candidates", [])) if isinstance(compare, dict) else 0, "pair_drift_flags": {}}
    for pair, row in drift.get("pairs", {}).items():
        payload["pair_drift_flags"][pair] = {"governance_changed": row.get("governance_changed"), "trading_mode_changed": row.get("trading_mode_changed"), "entry_changed": row.get("entry_changed")}
    out = Path("agent_service/reports/daily_ops_summary.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
