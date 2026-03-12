from __future__ import annotations

from typing import Dict, List

from agent_service.providers.market_data.tradingview_mcp_provider import TradingViewMcpProvider
from agent_service.providers.onchain.dexpaprika_provider import DexPaprikaProvider
from agent_service.providers.provider_base import SkillProvider


def build_default_provider_registry() -> Dict[str, SkillProvider]:
    return {
        "tradingview_mcp": TradingViewMcpProvider(default_timeframe="1h"),
        "dexpaprika": DexPaprikaProvider(),
    }


def build_pair_provider_map(pairs: List[str]) -> Dict[str, List[SkillProvider]]:
    registry = build_default_provider_registry()
    pair_map: Dict[str, List[SkillProvider]] = {}
    for pair in pairs:
        pair_map[pair] = [provider for provider in registry.values() if provider.supports_pair(pair)]
    return pair_map
