class NewsPolicy:
    def __init__(self, config): self.config = config or {}
    def global_defaults(self):
        return self.config.get("global_defaults", {
            "high_priority_event_types":["regulatory_action","exchange_incident","macro_official_update"],
            "block_on_event_types":["exchange_incident"],
            "review_on_event_types":["regulatory_action","fallback_event","social_buzz"],
            "minimum_credibility_for_action":0.70,
            "escalate_on_exchange_status":True,
            "escalate_on_regulatory":True
        })
    def pair_overrides(self):
        raw = self.config.get("pair_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}
    def config_for_pair(self, pair):
        cfg = dict(self.global_defaults()); cfg.update(self.pair_overrides().get(str(pair).upper(), {})); return cfg
    def high_priority_event_types(self, pair): return list(self.config_for_pair(pair).get("high_priority_event_types", []))
    def block_on_event_types(self, pair): return list(self.config_for_pair(pair).get("block_on_event_types", []))
    def review_on_event_types(self, pair): return list(self.config_for_pair(pair).get("review_on_event_types", []))
