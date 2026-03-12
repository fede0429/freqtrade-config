from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from agent_service.aggregator.decision_aggregator import DecisionAggregator
from agent_service.aggregator.provider_health_report import write_provider_health_report
from agent_service.providers.provider_base import ProviderSnapshot, SkillProvider
from agent_service.providers.provider_registry import (
    build_default_provider_registry,
    build_pair_provider_map,
)


DEFAULT_PAIRS = ["BTC/USDT", "ETH/USDT"]


def collect_pair_snapshots(pair_provider_map: Dict[str, List[SkillProvider]]) -> Dict[str, List[ProviderSnapshot]]:
    pair_snapshots: Dict[str, List[ProviderSnapshot]] = {}
    for pair, providers in pair_provider_map.items():
        snapshots: List[ProviderSnapshot] = []
        for provider in providers:
            if provider.kind == "market_data":
                snapshots.append(provider.fetch(pair, {"timeframe": "1h"}))
            else:
                snapshots.append(provider.fetch(pair))
        pair_snapshots[pair] = snapshots
    return pair_snapshots


def main():
    providers = build_default_provider_registry()
    write_provider_health_report(providers)

    pair_provider_map = build_pair_provider_map(DEFAULT_PAIRS)
    pair_snapshots = collect_pair_snapshots(pair_provider_map)

    aggregator = DecisionAggregator(cache_ttl_seconds=90, shadow_mode=True)
    out = aggregator.write_decision_cache(pair_snapshots)
    print(out)


if __name__ == "__main__":
    main()
