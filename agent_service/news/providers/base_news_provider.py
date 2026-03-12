from abc import ABC, abstractmethod

class BaseNewsProvider(ABC):
    name = "base_news_provider"
    source_tier = "unknown"

    @abstractmethod
    def fetch_raw_items(self): ...
    @abstractmethod
    def build_events(self): ...
