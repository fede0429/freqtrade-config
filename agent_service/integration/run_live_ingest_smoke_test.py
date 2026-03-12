import json
from pathlib import Path
from agent_service.integration.runtime_settings import RuntimeSettings
from agent_service.news.ingestion.rss_source_registry import load_rss_source_registry
from agent_service.news.ingestion.rss_source_adapter import RSSSourceAdapter

def main():
    settings = RuntimeSettings.from_env()
    registry = load_rss_source_registry()
    adapter = RSSSourceAdapter(timeout_seconds=settings.request_timeout_seconds)
    payload = {"llm_enabled": settings.llm_enabled(), "social_enabled": settings.social_enabled(), "rss_sources": []}
    try:
        rows = adapter.fetch_all(registry)
        for row in rows:
            payload["rss_sources"].append({"source_name": row.get("source_name"), "source_tier": row.get("source_tier"), "item_count": row.get("item_count", 0), "url": row.get("url")})
        payload["status"] = "ok"
    except Exception as e:
        payload["status"] = "degraded"
        payload["error"] = str(e)
    out = Path("agent_service/reports/live_ingest_smoke_test.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
