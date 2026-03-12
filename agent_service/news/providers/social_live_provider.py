from agent_service.news.ingestion.social_api_clients import XApiClient, RedditApiClient
from agent_service.news.llm.sentiment_reasoner import SentimentReasoner
from agent_service.news.models import RawNewsItem
from agent_service.news.normalize.event_normalizer import EventNormalizer
from agent_service.news.providers.base_news_provider import BaseNewsProvider

class SocialLiveProvider(BaseNewsProvider):
    name = "social_live_provider"
    source_tier = "social"

    def __init__(self, llm_client, x_client=None, reddit_client=None):
        self.reasoner = SentimentReasoner(llm_client)
        self.normalizer = EventNormalizer()
        self.x_client = x_client
        self.reddit_client = reddit_client

    def fetch_raw_items(self):
        items = []
        if self.x_client:
            for row in self.x_client.search_recent("bitcoin OR ethereum", max_results=10):
                items.append(RawNewsItem(source_name="x_api_live", source_type="api", category="social", title=row.get("text","")[:140], body=row.get("text",""), url=row.get("url",""), published_at=row.get("created_at",""), metadata={"platform":"x"}))
        if self.reddit_client:
            for row in self.reddit_client.search_posts("bitcoin ethereum", limit=10):
                items.append(RawNewsItem(source_name="reddit_api_live", source_type="api", category="social", title=row.get("title",""), body=row.get("selftext",""), url=row.get("url",""), published_at=row.get("created_at",""), metadata={"platform":"reddit"}))
        return items

    def build_events(self):
        events = []
        for item in self.fetch_raw_items():
            result = self.reasoner.analyze(item.title, item.body, item.source_name)
            events.append(self.normalizer.normalize(item=item, event_type=result.get("event_type","social_buzz"), summary=result.get("summary","social_live_event"), sentiment_score=float(result.get("sentiment_score",0.0)), credibility_score=0.45, impact_horizon=result.get("impact_horizon","intraday"), affected_assets=list(result.get("affected_assets",[])), market_regime_bias=result.get("market_regime_bias","neutral"), risk_flags=list(result.get("risk_flags",[])), review_required=True, source_tier=self.source_tier))
        return events
