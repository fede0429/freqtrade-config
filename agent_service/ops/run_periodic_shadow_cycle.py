import json, subprocess
from pathlib import Path
from datetime import datetime, timezone
from agent_service.ops.append_run_history import append_run_history

STEPS = [
    ["python","agent_service/orchestration/run_shadow_pipeline.py"],
    ["python","agent_service/calibration/build_live_calibration_compare.py"],
    ["python","agent_service/calibration/build_pair_drift_summary.py"],
    ["python","agent_service/ops/build_runtime_readiness_report.py"],
    ["python","agent_service/ops/build_daily_ops_summary.py"],
]

def utc_now_iso(): return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    step_results = []
    for cmd in STEPS:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        step_results.append({"cmd": cmd, "returncode": completed.returncode, "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:], "status": "ok" if completed.returncode == 0 else "failed"})
    shadow_summary = load_json("agent_service/reports/shadow_run_summary.json", {})
    readiness = load_json("agent_service/reports/runtime_readiness_report.json", {})
    daily = load_json("agent_service/reports/daily_ops_summary.json", {})
    payload = {"ts": utc_now_iso(), "kind":"periodic_shadow_cycle", "step_results": step_results, "shadow_run_status": shadow_summary.get("status"), "runtime_readiness_status": readiness.get("overall_status"), "daily_ops_summary_status": daily.get("runtime_readiness_status")}
    append_run_history(payload)
    out = Path("agent_service/reports/periodic_shadow_cycle_report.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
