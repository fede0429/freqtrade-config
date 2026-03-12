import json, os
from pathlib import Path

def has_env(name): return bool(os.getenv(name, ""))

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    smoke = load_json("agent_service/reports/live_ingest_smoke_test.json", {})
    compare = load_json("agent_service/reports/live_calibration_compare_report.json", {})
    summary = load_json("agent_service/reports/shadow_run_summary.json", {})
    payload = {"kind":"runtime_readiness_report","env":{"llm_endpoint":has_env("NEWS_LLM_API_ENDPOINT"),"llm_key":has_env("NEWS_LLM_API_KEY"),"llm_model":has_env("NEWS_LLM_MODEL"),"x_bearer_token":has_env("X_BEARER_TOKEN"),"reddit_client_id":has_env("REDDIT_CLIENT_ID"),"reddit_client_secret":has_env("REDDIT_CLIENT_SECRET")},"smoke_test_status": smoke.get("status"), "shadow_run_status": summary.get("status"), "compare_available": bool(compare), "top_candidate_count": len(compare.get("candidate_ranking", {}).get("top_candidates", [])) if isinstance(compare, dict) else 0}
    env_ok = payload["env"]["llm_endpoint"] and payload["env"]["llm_key"] and payload["env"]["llm_model"]
    payload["overall_status"] = "ok" if env_ok and payload["smoke_test_status"] in {"ok","degraded"} else "degraded"
    out = Path("agent_service/reports/runtime_readiness_report.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
