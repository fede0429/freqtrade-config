from agent_service.news.ingestion.rss_fetcher import RSSFetcher
from agent_service.news.ingestion.rss_source_registry import enabled_sources

class RSSSourceAdapter:
    def __init__(self, timeout_seconds=30): self.fetcher = RSSFetcher(timeout_seconds=timeout_seconds)
    def fetch_all(self, registry):
        rows = []
        for source in enabled_sources(registry):
            fetched = self.fetcher.fetch(source["url"])
            rows.append({"source_name": source.get("source_name"), "source_tier": source.get("source_tier"), "url": source.get("url"), "item_count": len(fetched), "items": fetched})
        return rows
