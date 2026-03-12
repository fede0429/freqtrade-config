from dataclasses import asdict
from agent_service.providers.provider_base import ProviderSnapshot, utc_now_iso

class NewsEventToSnapshotMapper:
    PROVIDER_NAME_BY_TIER = {
        "official": "official_news_skill",
        "exchange_status": "exchange_status_skill",
        "media": "media_news_skill",
        "social": "social_signal_skill",
        "fallback": "crawler_fallback_skill",
    }

    def provider_name(self, source_tier):
        return self.PROVIDER_NAME_BY_TIER.get(source_tier, "generic_news_skill")

    def score_from_event(self, event):
        sentiment = abs(float(event.sentiment_score))
        credibility = float(event.credibility_score)
        return round(min(1.0, max(0.0, 0.55 * credibility + 0.45 * sentiment)), 4)

    def risk_flags_from_event(self, event):
        flags = list(event.risk_flags)
        if event.review_required:
            flags.append("review_required")
        return sorted(set(flags))

    def map_event(self, pair, event):
        signals = {
            "event_type": event.event_type,
            "headline": event.headline,
            "summary": event.summary,
            "sentiment_score": event.sentiment_score,
            "credibility_score": event.credibility_score,
            "impact_horizon": event.impact_horizon,
            "market_regime_bias": event.market_regime_bias,
            "affected_assets": event.affected_assets,
            "source_name": event.source_name,
            "source_tier": event.source_tier,
        }
        raw_ref = asdict(event)
        raw_ref["signals"] = signals
        raw_ref["event_type"] = event.event_type
        raw_ref["credibility_score"] = event.credibility_score
        raw_ref["source_tier"] = event.source_tier
        return ProviderSnapshot(
            provider=self.provider_name(event.source_tier),
            kind="news_signal",
            pair=pair,
            status="ok",
            ts=utc_now_iso(),
            latency_ms=400,
            stale=False,
            score=self.score_from_event(event),
            signals=signals,
            risk_flags=self.risk_flags_from_event(event),
            raw_ref=raw_ref,
        )

    def map_events_for_pair(self, pair, events):
        return [self.map_event(pair, e) for e in events]
