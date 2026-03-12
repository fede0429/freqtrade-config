class TradingViewMcpProvider:
    name='tradingview_mcp'; kind='market_data'
    def __init__(self, default_timeframe='1h'): self.default_timeframe=default_timeframe
    def health(self):
        from agent_service.providers.provider_base import ProviderHealth, utc_now_iso
        return ProviderHealth(self.name,self.kind,'ok',utc_now_iso(),'snapshot_provider')
    def supports_pair(self,pair): return '/' in pair
    def fetch(self,pair,context=None):
        from agent_service.providers.provider_base import ProviderSnapshot, utc_now_iso
        return ProviderSnapshot(self.name,self.kind,pair,'ok',utc_now_iso(),200,False,0.76,{'trend':'bullish'},[],{})
