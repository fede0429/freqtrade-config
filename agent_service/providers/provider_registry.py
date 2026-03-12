from agent_service.providers.market_data.tradingview_mcp_provider import TradingViewMcpProvider
from agent_service.providers.onchain.dexpaprika_provider import DexPaprikaProvider

def build_default_provider_registry():
    return {'tradingview_mcp': TradingViewMcpProvider('1h'), 'dexpaprika': DexPaprikaProvider()}
