from agent_service.aggregator.decision_aggregator import DecisionAggregator
from agent_service.providers.provider_registry import build_default_provider_registry

def main():
    reg=build_default_provider_registry()
    pair_snapshots={'BTC/USDT':[reg['tradingview_mcp'].fetch('BTC/USDT',{'timeframe':'1h'}), reg['dexpaprika'].fetch('BTC/USDT')], 'ETH/USDT':[reg['tradingview_mcp'].fetch('ETH/USDT',{'timeframe':'1h'}), reg['dexpaprika'].fetch('ETH/USDT')]}
    out=DecisionAggregator().write_decision_cache(pair_snapshots)
    print(out)

if __name__=='__main__':
    main()
