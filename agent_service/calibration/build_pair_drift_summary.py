import json
from pathlib import Path

LIVE_COMPARE_PATH = "agent_service/reports/live_calibration_compare_report.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    report = load_json(LIVE_COMPARE_PATH, {"drift_summary": {"pairs": {}}})
    out = Path("agent_service/reports/pair_drift_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.get("drift_summary", {}), indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
