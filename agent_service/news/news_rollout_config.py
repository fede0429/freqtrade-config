class NewsRolloutConfig:
    def __init__(self, config): self.config = config or {}
    def enabled_pairs(self): return [str(v).upper() for v in self.config.get("enabled_pairs", [])]
    def pair_overrides(self):
        raw = self.config.get("pair_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}
    def is_pair_enabled(self, pair):
        pairs = self.enabled_pairs()
        return not pairs or str(pair).upper() in pairs
    def enabled_source_tiers_for_pair(self, pair):
        pair = str(pair).upper()
        overrides = self.pair_overrides().get(pair, {})
        if "enabled_source_tiers" in overrides:
            return list(overrides["enabled_source_tiers"])
        return list(self.config.get("enabled_source_tiers", ["official","exchange_status","media","social"]))
    def max_events_per_pair(self, pair):
        pair = str(pair).upper()
        overrides = self.pair_overrides().get(pair, {})
        return int(overrides.get("max_events_per_pair", self.config.get("max_events_per_pair", 8)))
