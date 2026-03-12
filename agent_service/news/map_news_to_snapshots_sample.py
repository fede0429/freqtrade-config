import json
from dataclasses import asdict
from agent_service.news.llm.llm_client import LLMClient
from agent_service.news.mappers.news_event_to_snapshot_mapper import NewsEventToSnapshotMapper
from agent_service.news.normalize.deduper import EventDeduper
from agent_service.news.providers.official_news_provider import OfficialNewsProvider
from agent_service.news.providers.exchange_status_provider import ExchangeStatusProvider
from agent_service.news.providers.media_rss_provider import MediaRssProvider
from agent_service.news.providers.social_signal_provider import SocialSignalProvider

def main():
    llm_client = LLMClient()
    providers = [OfficialNewsProvider(llm_client), ExchangeStatusProvider(llm_client), MediaRssProvider(llm_client), SocialSignalProvider(llm_client)]
    events = []
    for provider in providers:
        events.extend(provider.build_events())
    deduped = EventDeduper().dedupe(events)
    mapper = NewsEventToSnapshotMapper()
    snapshots = mapper.map_events_for_pair("BTC/USDT", deduped)
    print(json.dumps([asdict(s) for s in snapshots], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
