import os
from dataclasses import dataclass

@dataclass
class RuntimeSettings:
    news_llm_api_endpoint: str
    news_llm_api_key: str
    news_llm_model: str
    x_bearer_token: str
    reddit_client_id: str
    reddit_client_secret: str
    request_timeout_seconds: int = 30

    @classmethod
    def from_env(cls):
        return cls(
            news_llm_api_endpoint=os.getenv("NEWS_LLM_API_ENDPOINT", ""),
            news_llm_api_key=os.getenv("NEWS_LLM_API_KEY", ""),
            news_llm_model=os.getenv("NEWS_LLM_MODEL", ""),
            x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        )

    def llm_enabled(self): return bool(self.news_llm_api_endpoint and self.news_llm_api_key and self.news_llm_model)
    def social_enabled(self): return bool(self.x_bearer_token or (self.reddit_client_id and self.reddit_client_secret))
