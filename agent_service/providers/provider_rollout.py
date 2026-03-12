from typing import Dict, List, Any

def _upper_pairs(values: List[str]) -> List[str]:
    return [str(v).upper() for v in values]

class ProviderRolloutPolicy:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}

    def enabled_pairs(self) -> List[str]:
        return _upper_pairs(self.config.get("enabled_pairs", []))

    def provider_defaults(self) -> Dict[str, Any]:
        return self.config.get("provider_defaults", {})

    def pair_overrides(self) -> Dict[str, Any]:
        raw = self.config.get("pair_provider_overrides", {})
        return {str(k).upper(): v for k, v in raw.items()}

    def is_pair_enabled(self, pair: str) -> bool:
        pairs = self.enabled_pairs()
        return not pairs or pair.upper() in pairs

    def enabled_providers_for_pair(self, pair: str, available_provider_names: List[str]) -> List[str]:
        pair = pair.upper()
        if not self.is_pair_enabled(pair):
            return []
        defaults = self.provider_defaults()
        overrides = self.pair_overrides().get(pair, {})
        disabled = set(_upper_pairs(overrides.get("disabled_providers", [])))
        forced = set(_upper_pairs(overrides.get("forced_providers", [])))
        enabled = []
        for name in list(available_provider_names):
            upper = name.upper()
            default_enabled = bool(defaults.get(name, True))
            if upper in disabled:
                continue
            if default_enabled or upper in forced:
                enabled.append(name)
        return enabled
