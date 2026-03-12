import json
from pathlib import Path

DEFAULT_PATH = "user_data/config/rss_source_registry.json"

def load_rss_source_registry(path=DEFAULT_PATH):
    p = Path(path)
    if not p.exists():
        return {"sources":[{"source_name":"sec_press_releases","url":"","source_tier":"official","enabled":False},{"source_name":"federal_reserve_press_releases","url":"","source_tier":"official","enabled":False},{"source_name":"coindesk_rss","url":"","source_tier":"media","enabled":False}]}
    return json.loads(p.read_text(encoding="utf-8"))

def enabled_sources(registry):
    return [row for row in registry.get("sources", []) if bool(row.get("enabled", False)) and row.get("url")]
