from agent_service.news.models import RawNewsItem
from agent_service.news.normalize.event_normalizer import EventNormalizer
from agent_service.news.providers.base_news_provider import BaseNewsProvider

class ExchangeStatusProvider(BaseNewsProvider):
    name = "exchange_status_provider"
    source_tier = "exchange_status"

    def __init__(self, llm_client):
        self.normalizer = EventNormalizer()

    def fetch_raw_items(self):
        return [RawNewsItem("coinbase_exchange_status","status_feed","exchange_status","Degraded performance on trading API","Incident affecting exchange API latency.","https://example.com/status-incident","2026-03-11T12:05:00Z",{"source_priority":95})]

    def build_events(self):
        events=[]
        for item in self.fetch_raw_items():
            events.append(self.normalizer.normalize(
                item=item, event_type="exchange_incident", summary="exchange_status_incident",
                sentiment_score=-0.25, credibility_score=0.99, impact_horizon="intraday",
                affected_assets=[], market_regime_bias="risk_off",
                risk_flags=["exchange_status_incident"], review_required=False,
                source_tier=self.source_tier
            ))
        return events
