import json
from dataclasses import asdict
from pathlib import Path
from agent_service.aggregator.decision_aggregator import DecisionAggregator
from agent_service.news.llm.llm_client import LLMClient
from agent_service.news.mappers.news_event_to_snapshot_mapper import NewsEventToSnapshotMapper
from agent_service.news.news_rollout_config import NewsRolloutConfig
from agent_service.news.normalize.deduper import EventDeduper
from agent_service.news.providers.official_news_provider import OfficialNewsProvider
from agent_service.news.providers.exchange_status_provider import ExchangeStatusProvider
from agent_service.news.providers.media_rss_provider import MediaRssProvider
from agent_service.news.providers.social_signal_provider import SocialSignalProvider
from agent_service.news.providers.crawler_fallback_provider import CrawlerFallbackProvider
from agent_service.news.reports.news_aggregation_report import write_news_aggregation_report
from agent_service.news.reports.news_provider_health_report import write_news_provider_health_report
from agent_service.providers.provider_registry import build_pair_provider_map

DEFAULT_PAIRS = ["BTC/USDT","ETH/USDT"]
NEWS_ROLLOUT_CONFIG_PATH = "user_data/config/news_rollout.json"
PROVIDER_ROLLOUT_CONFIG_PATH = "user_data/config/provider_rollout.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def build_news_providers(llm_client):
    return [OfficialNewsProvider(llm_client), ExchangeStatusProvider(llm_client), MediaRssProvider(llm_client), SocialSignalProvider(llm_client), CrawlerFallbackProvider(llm_client)]

def provider_health_summary(providers):
    return {"providers": {provider.name: {"provider": provider.name, "source_tier": provider.source_tier, "status": "ok", "enabled": True} for provider in providers}}

def collect_news_events_for_pair(pair, news_rollout, providers):
    deduper = EventDeduper()
    enabled_tiers = set(news_rollout.enabled_source_tiers_for_pair(pair))
    max_events = news_rollout.max_events_per_pair(pair)
    events = []
    for provider in providers:
        if provider.source_tier not in enabled_tiers:
            continue
        events.extend(provider.build_events())
    return deduper.dedupe(events)[:max_events]

def main():
    provider_rollout = load_json(PROVIDER_ROLLOUT_CONFIG_PATH, {"enabled_pairs": DEFAULT_PAIRS, "provider_defaults": {"tradingview_mcp": True, "dexpaprika": True}, "pair_provider_overrides": {}})
    news_rollout = NewsRolloutConfig(load_json(NEWS_ROLLOUT_CONFIG_PATH, {"enabled_pairs": DEFAULT_PAIRS, "enabled_source_tiers": ["official","exchange_status","media","social"], "max_events_per_pair": 8, "pair_overrides": {}}))
    pairs = provider_rollout.get("enabled_pairs", DEFAULT_PAIRS)
    base_pair_provider_map = build_pair_provider_map(pairs, rollout_config=provider_rollout)
    llm_client = LLMClient()
    news_providers = build_news_providers(llm_client)
    write_news_provider_health_report(provider_health_summary(news_providers))
    mapper = NewsEventToSnapshotMapper()
    pair_snapshots = {}
    aggregation_report = {"pairs": {}}
    for pair, base_providers in base_pair_provider_map.items():
        base_snapshots = [provider.fetch(pair, {"timeframe": "1h"}) if getattr(provider, "kind", "") == "market_data" else provider.fetch(pair) for provider in base_providers]
        news_events = collect_news_events_for_pair(pair, news_rollout, news_providers) if news_rollout.is_pair_enabled(pair) else []
        news_snapshots = mapper.map_events_for_pair(pair, news_events)
        pair_snapshots[pair] = base_snapshots + news_snapshots
        aggregation_report["pairs"][pair] = {"base_provider_count": len(base_snapshots), "news_event_count": len(news_events), "news_snapshot_count": len(news_snapshots), "enabled_source_tiers": news_rollout.enabled_source_tiers_for_pair(pair), "news_events": [asdict(e) for e in news_events]}
    write_news_aggregation_report(aggregation_report)
    out = DecisionAggregator(cache_ttl_seconds=90, shadow_mode=True).write_decision_cache(pair_snapshots)
    print(out)

if __name__ == "__main__":
    main()
