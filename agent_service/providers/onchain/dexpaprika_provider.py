class DexPaprikaProvider:
    name='dexpaprika'; kind='onchain_liquidity'
    def health(self):
        from agent_service.providers.provider_base import ProviderHealth, utc_now_iso
        return ProviderHealth(self.name,self.kind,'ok',utc_now_iso(),'snapshot_provider')
    def supports_pair(self,pair): return '/' in pair
    def fetch(self,pair,context=None):
        from agent_service.providers.provider_base import ProviderSnapshot, utc_now_iso
        return ProviderSnapshot(self.name,self.kind,pair,'ok',utc_now_iso(),250,False,0.68,{'liquidity_usd':2450000},[],{})
