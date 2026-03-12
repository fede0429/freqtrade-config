import json
from pathlib import Path
from agent_service.calibration.live_compare_utils import compare_pair_rows

BASELINE_PATH = "agent_service/reports/shadow_compare_baseline.json"
DECISION_CACHE_PATH = "user_data/agent_runtime/state/decision_cache.json"
CALIBRATION_REPORT_PATH = "agent_service/reports/calibration_report.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def build_pair_compare(baseline, current_cache):
    out = {}
    baseline_pairs = baseline.get("pairs", {})
    current_pairs = current_cache.get("pairs", {})
    for pair in sorted(set(baseline_pairs.keys()) | set(current_pairs.keys())):
        out[pair] = compare_pair_rows(baseline_pairs.get(pair, {}), current_pairs.get(pair, {}))
    return out

def build_candidate_ranking(calibration_report):
    candidates = calibration_report.get("top_candidates", [])
    return {"candidate_count": len(candidates), "top_candidates": candidates[:10]}

def main():
    baseline = load_json(BASELINE_PATH, {"pairs": {}})
    current_cache = load_json(DECISION_CACHE_PATH, {"pairs": {}})
    calibration_report = load_json(CALIBRATION_REPORT_PATH, {"top_candidates": []})
    pair_compare = build_pair_compare(baseline, current_cache)
    drift_summary = {"pairs": {}}
    for pair, row in pair_compare.items():
        drift_summary["pairs"][pair] = {"confidence_delta": row.get("confidence_delta"), "governance_changed": row.get("governance_gate_baseline") != row.get("governance_gate_current"), "trading_mode_changed": row.get("trading_mode_baseline") != row.get("trading_mode_current"), "entry_changed": row.get("entry_allowed_baseline") != row.get("entry_allowed_current")}
    payload = {"schema_version": "1.0", "kind": "live_calibration_compare", "pair_compare": pair_compare, "drift_summary": drift_summary, "candidate_ranking": build_candidate_ranking(calibration_report)}
    out = Path("agent_service/reports/live_calibration_compare_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
