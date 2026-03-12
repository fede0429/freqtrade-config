import hashlib
from agent_service.news.models import NormalizedEvent

class EventNormalizer:
    def build_event_id(self, item):
        key = f"{item.source_name}|{item.title}|{item.published_at}|{item.url}"
        return "evt_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def normalize(self, item, event_type, summary, sentiment_score, credibility_score, impact_horizon, affected_assets, market_regime_bias, risk_flags, review_required, source_tier):
        return NormalizedEvent(
            event_id=self.build_event_id(item),
            source_name=item.source_name,
            source_tier=source_tier,
            event_type=event_type,
            headline=item.title,
            summary=summary,
            sentiment_score=sentiment_score,
            credibility_score=credibility_score,
            impact_horizon=impact_horizon,
            affected_assets=affected_assets,
            market_regime_bias=market_regime_bias,
            risk_flags=risk_flags,
            review_required=review_required,
            published_at=item.published_at,
            url=item.url,
            raw_metadata=item.metadata,
        )
