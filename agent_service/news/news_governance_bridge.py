class NewsGovernanceBridge:
    NEWS_PROVIDER_PREFIXES = ("official_news_skill","exchange_status_skill","media_news_skill","social_signal_skill","crawler_fallback_skill")
    def is_news_provider(self, provider_name): return str(provider_name).startswith(self.NEWS_PROVIDER_PREFIXES)
    def extract_news_provider_meta(self, pair_meta):
        providers = pair_meta.get("providers", {})
        return [{"provider": name, **meta} for name, meta in providers.items() if self.is_news_provider(name)]
    def extract_news_event_signals(self, pair_meta):
        providers = pair_meta.get("providers", {})
        trace = pair_meta.get("trace", {})
        refs = trace.get("evidence_refs", [])
        out = []
        for provider_name in providers.keys():
            if self.is_news_provider(provider_name):
                out.append({"provider": provider_name, "evidence_refs": [r for r in refs if str(r).startswith(provider_name)]})
        return out
