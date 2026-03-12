from typing import Dict, List
from agent_service.providers.market_data.tradingview_mcp_provider import TradingViewMcpProvider
from agent_service.providers.onchain.dexpaprika_provider import DexPaprikaProvider
from agent_service.providers.provider_rollout import ProviderRolloutPolicy

def build_default_provider_registry() -> Dict[str, object]:
    return {"tradingview_mcp": TradingViewMcpProvider(default_timeframe="1h"), "dexpaprika": DexPaprikaProvider()}

def build_pair_provider_map(pairs: List[str], rollout_config: dict | None = None) -> Dict[str, list]:
    registry = build_default_provider_registry()
    policy = ProviderRolloutPolicy(rollout_config or {})
    out: Dict[str, list] = {}
    for pair in pairs:
        enabled_names = policy.enabled_providers_for_pair(pair, list(registry.keys()))
        out[pair] = [registry[n] for n in enabled_names if n in registry and registry[n].supports_pair(pair)]
    return out
