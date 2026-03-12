class ProviderRolloutPolicy:
    def __init__(self, config): self.config=config or {}
    def enabled_pairs(self): return [str(v).upper() for v in self.config.get('enabled_pairs', [])]
