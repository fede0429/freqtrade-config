from __future__ import annotations

from typing import Dict, List

from agent_service.providers.market_data.tradingview_mcp_provider import TradingViewMcpProvider
from agent_service.providers.onchain.dexpaprika_provider import DexPaprikaProvider
from agent_service.providers.provider_base import SkillProvider
from agent_service.providers.provider_rollout import ProviderRolloutPolicy


def build_default_provider_registry() -> Dict[str, SkillProvider]:
    return {
        "tradingview_mcp": TradingViewMcpProvider(default_timeframe="1h"),
        "dexpaprika": DexPaprikaProvider(),
    }


def build_pair_provider_map(
    pairs: List[str],
    rollout_config: dict | None = None,
) -> Dict[str, List[SkillProvider]]:
    registry = build_default_provider_registry()
    policy = ProviderRolloutPolicy(rollout_config or {})
    pair_map: Dict[str, List[SkillProvider]] = {}

    for pair in pairs:
        enabled_names = policy.enabled_providers_for_pair(pair, list(registry.keys()))
        providers = []
        for name in enabled_names:
            provider = registry.get(name)
            if provider is None:
                continue
            if provider.supports_pair(pair):
                providers.append(provider)
        pair_map[pair] = providers
    return pair_map
