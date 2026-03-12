from agent_service.news.ingestion.rss_source_adapter import RSSSourceAdapter
from agent_service.news.ingestion.rss_source_registry import load_rss_source_registry
from agent_service.news.llm.macro_reasoner import MacroReasoner
from agent_service.news.models import RawNewsItem
from agent_service.news.normalize.event_normalizer import EventNormalizer
from agent_service.news.providers.base_news_provider import BaseNewsProvider

class OfficialRssRegistryProvider(BaseNewsProvider):
    name = "official_rss_registry_provider"
    source_tier = "official"

    def __init__(self, llm_client, registry_path="user_data/config/rss_source_registry.json"):
        self.reasoner = MacroReasoner(llm_client)
        self.normalizer = EventNormalizer()
        self.registry_path = registry_path
        self.adapter = RSSSourceAdapter()

    def fetch_raw_items(self):
        registry = load_rss_source_registry(self.registry_path)
        rows = self.adapter.fetch_all(registry)
        out = []
        for row in rows:
            if row.get("source_tier") != "official": continue
            for item in row.get("items", []):
                out.append(RawNewsItem(source_name=row.get("source_name","official_rss_registry"), source_type="rss", category="official", title=item.get("title",""), body=item.get("description",""), url=item.get("link",""), published_at=item.get("pubDate",""), metadata={"feed_url": row.get("url","")}))
        return out

    def build_events(self):
        events = []
        for item in self.fetch_raw_items():
            result = self.reasoner.analyze(item.title, item.body, item.source_name)
            events.append(self.normalizer.normalize(item=item, event_type=result.get("event_type","official_update"), summary=result.get("summary","official_registry_event"), sentiment_score=float(result.get("sentiment_score",0.0)), credibility_score=0.98, impact_horizon=result.get("impact_horizon","intraday"), affected_assets=list(result.get("affected_assets",[])), market_regime_bias=result.get("market_regime_bias","neutral"), risk_flags=list(result.get("risk_flags",[])), review_required=bool(result.get("review_required",False)), source_tier=self.source_tier))
        return events
