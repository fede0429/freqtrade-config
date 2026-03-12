import subprocess
from datetime import datetime, timezone
from agent_service.orchestration.shadow_run_manifest import write_shadow_run_manifest
from agent_service.orchestration.shadow_run_summary import write_shadow_run_summary

STEPS = [
    {"name":"live_ingest_smoke_test","cmd":["python","agent_service/integration/run_live_ingest_smoke_test.py"]},
    {"name":"source_fetch_report","cmd":["python","agent_service/integration/build_source_fetch_report.py"]},
    {"name":"news_event_pack","cmd":["python","agent_service/news/build_news_event_pack.py"]},
    {"name":"decision_cache_with_news","cmd":["python","agent_service/news/integrate_news_into_decision_cache.py"]},
    {"name":"news_governance_overlay","cmd":["python","agent_service/news/apply_news_governance_overlay.py"]},
    {"name":"news_review_pack","cmd":["python","agent_service/news/build_news_review_pack.py"]},
    {"name":"news_quality_pack","cmd":["python","agent_service/news/build_news_quality_pack.py"]},
    {"name":"shadow_calibration","cmd":["python","agent_service/calibration/run_shadow_calibration.py"]},
    {"name":"shadow_compare_baseline","cmd":["python","agent_service/orchestration/build_shadow_compare_baseline.py"]},
]

def utc_now_iso(): return datetime.now(timezone.utc).isoformat()

def run_step(step):
    try:
        completed = subprocess.run(step["cmd"], capture_output=True, text=True, check=False)
        return {"name": step["name"], "cmd": step["cmd"], "returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:], "status": "ok" if completed.returncode == 0 else "failed"}
    except Exception as e:
        return {"name": step["name"], "cmd": step["cmd"], "status": "failed", "error": str(e)}

def main():
    steps_result = [run_step(step) for step in STEPS]
    write_shadow_run_manifest({"ts": utc_now_iso(), "kind": "shadow_run_manifest", "steps": steps_result})
    ok_count = sum(1 for row in steps_result if row.get("status") == "ok")
    failed = [row["name"] for row in steps_result if row.get("status") != "ok"]
    write_shadow_run_summary({"ts": utc_now_iso(), "kind": "shadow_run_summary", "total_steps": len(steps_result), "ok_steps": ok_count, "failed_steps": failed, "status": "ok" if ok_count == len(steps_result) else "degraded"})
    print("agent_service/reports/shadow_run_summary.json")

if __name__ == "__main__":
    main()
