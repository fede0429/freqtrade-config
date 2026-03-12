from agent_service.news.models import RawNewsItem
from agent_service.news.normalize.event_normalizer import EventNormalizer
from agent_service.news.providers.base_news_provider import BaseNewsProvider

class MediaRssProvider(BaseNewsProvider):
    name = "media_rss_provider"
    source_tier = "media"

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.normalizer = EventNormalizer()

    def fetch_raw_items(self):
        return [RawNewsItem("coindesk_rss","rss","media","Bitcoin reacts to macro headline","Professional media coverage of a macro event affecting crypto sentiment.","https://example.com/coindesk-story","2026-03-11T12:15:00Z",{"source_priority":70})]

    def build_events(self):
        events=[]
        for item in self.fetch_raw_items():
            result = self.llm_client.classify_event(item.title, item.body, item.source_name)
            events.append(self.normalizer.normalize(
                item=item,
                event_type=result.get("event_type","media_interpretation"),
                summary=result.get("summary","media_event"),
                sentiment_score=float(result.get("sentiment_score",0.0)),
                credibility_score=0.75,
                impact_horizon=result.get("impact_horizon","intraday"),
                affected_assets=list(result.get("affected_assets",[])),
                market_regime_bias=result.get("market_regime_bias","neutral"),
                risk_flags=list(result.get("risk_flags",[])),
                review_required=bool(result.get("review_required",False)),
                source_tier=self.source_tier
            ))
        return events
