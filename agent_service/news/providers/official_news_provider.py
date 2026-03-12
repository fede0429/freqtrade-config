from agent_service.news.llm.macro_reasoner import MacroReasoner
from agent_service.news.models import RawNewsItem
from agent_service.news.normalize.event_normalizer import EventNormalizer
from agent_service.news.providers.base_news_provider import BaseNewsProvider

class OfficialNewsProvider(BaseNewsProvider):
    name = "official_news_provider"
    source_tier = "official"

    def __init__(self, llm_client):
        self.reasoner = MacroReasoner(llm_client)
        self.normalizer = EventNormalizer()

    def fetch_raw_items(self):
        return [RawNewsItem("sec_press_releases","rss","regulatory","Sample SEC Regulatory Update","Sample body for official source.","https://example.com/sec-update","2026-03-11T12:00:00Z",{"source_priority":100})]

    def build_events(self):
        events=[]
        for item in self.fetch_raw_items():
            result = self.reasoner.analyze(item.title, item.body, item.source_name)
            events.append(self.normalizer.normalize(
                item=item,
                event_type=result.get("event_type","regulatory_action"),
                summary=result.get("summary","official_event"),
                sentiment_score=float(result.get("sentiment_score",0.0)),
                credibility_score=0.98,
                impact_horizon=result.get("impact_horizon","intraday"),
                affected_assets=list(result.get("affected_assets",[])),
                market_regime_bias=result.get("market_regime_bias","neutral"),
                risk_flags=list(result.get("risk_flags",[])),
                review_required=bool(result.get("review_required",False)),
                source_tier=self.source_tier,
            ))
        return events
