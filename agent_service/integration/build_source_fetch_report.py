import json
from pathlib import Path
from agent_service.news.ingestion.rss_source_registry import load_rss_source_registry
from agent_service.news.ingestion.rss_source_adapter import RSSSourceAdapter

def main():
    rows = RSSSourceAdapter().fetch_all(load_rss_source_registry())
    payload = {"sources":[{"source_name": row.get("source_name"), "source_tier": row.get("source_tier"), "url": row.get("url"), "item_count": row.get("item_count", 0)} for row in rows]}
    out = Path("agent_service/reports/source_fetch_report.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
