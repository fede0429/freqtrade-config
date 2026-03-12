from agent_service.news.models import RawNewsItem
from agent_service.news.normalize.event_normalizer import EventNormalizer
from agent_service.news.providers.base_news_provider import BaseNewsProvider

class CrawlerFallbackProvider(BaseNewsProvider):
    name = "crawler_fallback_provider"
    source_tier = "fallback"

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.normalizer = EventNormalizer()

    def fetch_raw_items(self):
        return [RawNewsItem("crawler_fallback","crawler","fallback","Long-tail project update captured via crawler","Fallback crawler captured a project update page.","https://example.com/project-update","2026-03-11T12:20:00Z",{"source_priority":20})]

    def build_events(self):
        events=[]
        for item in self.fetch_raw_items():
            result = self.llm_client.classify_event(item.title, item.body, item.source_name)
            flags = list(set(list(result.get("risk_flags",[])) + ["fallback_source"]))
            events.append(self.normalizer.normalize(
                item=item,
                event_type=result.get("event_type","fallback_event"),
                summary=result.get("summary","fallback_event"),
                sentiment_score=float(result.get("sentiment_score",0.0)),
                credibility_score=0.25,
                impact_horizon=result.get("impact_horizon","intraday"),
                affected_assets=list(result.get("affected_assets",[])),
                market_regime_bias=result.get("market_regime_bias","neutral"),
                risk_flags=flags,
                review_required=True,
                source_tier=self.source_tier
            ))
        return events
