from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

from agent_service.aggregator.decision_aggregator import DecisionAggregator
from agent_service.aggregator.provider_health_report import write_provider_health_report
from agent_service.providers.provider_base import ProviderSnapshot, SkillProvider
from agent_service.providers.provider_registry import (
    build_default_provider_registry,
    build_pair_provider_map,
)
from agent_service.providers.provider_rollout import ProviderRolloutPolicy


DEFAULT_PAIRS = ["BTC/USDT", "ETH/USDT"]
ROLLOUT_CONFIG_PATH = "user_data/config/provider_rollout.json"


def load_rollout_config(path: str = ROLLOUT_CONFIG_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {
            "enabled_pairs": DEFAULT_PAIRS,
            "provider_defaults": {
                "tradingview_mcp": True,
                "dexpaprika": True,
            },
            "required_provider_names": ["tradingview_mcp", "dexpaprika"],
            "rollout_stage": "pair_provider_enablement_v1",
            "pair_provider_overrides": {},
        }
    return json.loads(p.read_text(encoding="utf-8"))


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


def build_rollout_report(
    rollout_config: dict,
    pair_provider_map: Dict[str, List[SkillProvider]],
) -> dict:
    policy = ProviderRolloutPolicy(rollout_config)
    report = {"pairs": {}}
    for pair, providers in pair_provider_map.items():
        report["pairs"][pair] = {
            "pair_enabled": policy.is_pair_enabled(pair),
            "rollout_stage": policy.rollout_stage_for_pair(pair),
            "required_providers": policy.required_providers_for_pair(pair),
            "enabled_providers": [p.name for p in providers],
        }
    return report


def write_rollout_report(report: dict, output_path: str = "agent_service/reports/provider_rollout_report.json") -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main():
    rollout_config = load_rollout_config()

    providers = build_default_provider_registry()
    write_provider_health_report(providers)

    pairs = rollout_config.get("enabled_pairs", DEFAULT_PAIRS)
    pair_provider_map = build_pair_provider_map(pairs, rollout_config=rollout_config)
    pair_snapshots = collect_pair_snapshots(pair_provider_map)

    rollout_report = build_rollout_report(rollout_config, pair_provider_map)
    write_rollout_report(rollout_report)

    aggregator = DecisionAggregator(cache_ttl_seconds=90, shadow_mode=True)
    out = aggregator.write_decision_cache(pair_snapshots)
    print(out)


if __name__ == "__main__":
    main()
