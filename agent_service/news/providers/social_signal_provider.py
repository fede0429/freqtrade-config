from agent_service.news.llm.sentiment_reasoner import SentimentReasoner
from agent_service.news.models import RawNewsItem
from agent_service.news.normalize.event_normalizer import EventNormalizer
from agent_service.news.providers.base_news_provider import BaseNewsProvider

class SocialSignalProvider(BaseNewsProvider):
    name = "social_signal_provider"
    source_tier = "social"

    def __init__(self, llm_client):
        self.reasoner = SentimentReasoner(llm_client)
        self.normalizer = EventNormalizer()

    def fetch_raw_items(self):
        return [RawNewsItem("x_api_v2","api","social","Crypto community is reacting to an exchange rumor","Fast-moving rumor on social channels.","https://example.com/social-post","2026-03-11T12:10:00Z",{"source_priority":45})]

    def build_events(self):
        events=[]
        for item in self.fetch_raw_items():
            result = self.reasoner.analyze(item.title, item.body, item.source_name)
            events.append(self.normalizer.normalize(
                item=item,
                event_type=result.get("event_type","social_buzz"),
                summary=result.get("summary","social_signal"),
                sentiment_score=float(result.get("sentiment_score",0.0)),
                credibility_score=0.45,
                impact_horizon=result.get("impact_horizon","intraday"),
                affected_assets=list(result.get("affected_assets",[])),
                market_regime_bias=result.get("market_regime_bias","neutral"),
                risk_flags=list(result.get("risk_flags",[])),
                review_required=True,
                source_tier=self.source_tier
            ))
        return events
