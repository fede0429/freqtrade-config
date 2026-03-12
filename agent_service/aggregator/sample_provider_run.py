from __future__ import annotations

import json

from agent_service.providers.market_data.tradingview_mcp_provider import TradingViewMcpProvider
from agent_service.providers.onchain.dexpaprika_provider import DexPaprikaProvider


def main():
    tv = TradingViewMcpProvider(default_timeframe="1h")
    dex = DexPaprikaProvider()

    rows = {
        "BTC/USDT": [
            tv.fetch("BTC/USDT", {"timeframe": "1h"}).__dict__,
            dex.fetch("BTC/USDT").__dict__,
        ],
        "ETH/USDT": [
            tv.fetch("ETH/USDT", {"timeframe": "1h"}).__dict__,
            dex.fetch("ETH/USDT").__dict__,
        ],
    }
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
