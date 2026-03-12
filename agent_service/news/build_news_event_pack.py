import json
from dataclasses import asdict
from pathlib import Path
from agent_service.news.llm.llm_client import LLMClient
from agent_service.news.normalize.deduper import EventDeduper
from agent_service.news.providers.official_news_provider import OfficialNewsProvider
from agent_service.news.providers.exchange_status_provider import ExchangeStatusProvider
from agent_service.news.providers.media_rss_provider import MediaRssProvider
from agent_service.news.providers.social_signal_provider import SocialSignalProvider
from agent_service.news.providers.crawler_fallback_provider import CrawlerFallbackProvider

def main():
    llm_client = LLMClient()
    providers = [OfficialNewsProvider(llm_client), ExchangeStatusProvider(llm_client), MediaRssProvider(llm_client), SocialSignalProvider(llm_client), CrawlerFallbackProvider(llm_client)]
    events = []
    for provider in providers:
        events.extend(provider.build_events())
    deduped = EventDeduper().dedupe(events)
    payload = {"schema_version":"1.0","kind":"news_event_pack","events":[asdict(e) for e in deduped]}
    out = Path("agent_service/reports/news_event_pack.json"); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
