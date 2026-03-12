import json
from pathlib import Path

FILES_TO_CHECK = ["user_data/config/rss_source_registry.json","user_data/config/news_rollout.json","user_data/config/news_policy.json","user_data/config/calibration_config.json","user_data/config/live_compare_config.json"]

def file_exists(path): return Path(path).exists()

def main():
    payload = {"kind":"preflight_checklist","config_files":{}, "env_checks":{"NEWS_LLM_API_ENDPOINT":False,"NEWS_LLM_API_KEY":False,"NEWS_LLM_MODEL":False,"X_BEARER_TOKEN":False,"REDDIT_CLIENT_ID":False,"REDDIT_CLIENT_SECRET":False}}
    for path in FILES_TO_CHECK: payload["config_files"][path] = {"exists": file_exists(path)}
    out = Path("agent_service/reports/preflight_checklist.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
