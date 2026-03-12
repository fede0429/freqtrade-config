import os
from agent_service.integration.http_utils import http_post_json

class LLMProviderRouter:
    def __init__(self) -> None:
        self.provider = os.getenv("NEWS_LLM_PROVIDER", "generic").strip().lower()
        self.endpoint = os.getenv("NEWS_LLM_API_ENDPOINT", "")
        self.api_key = os.getenv("NEWS_LLM_API_KEY", "")
        self.model = os.getenv("NEWS_LLM_MODEL", "")
        self.timeout_seconds = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.model)

    def build_payload(self, prompt):
        if self.provider in {"generic", "openai_compatible"}: return {"model": self.model, "input": prompt}
        if self.provider == "anthropic_compatible": return {"model": self.model, "messages": [{"role": "user", "content": str(prompt)}]}
        if self.provider == "gemini_compatible": return {"model": self.model, "contents": [prompt]}
        return {"model": self.model, "input": prompt}

    def parse_response(self, response):
        if isinstance(response, dict) and "event_type" in response: return response
        return {"event_type":"unknown","summary":"router_unparsed_response","sentiment_score":0.0,"impact_horizon":"intraday","affected_assets":[],"market_regime_bias":"neutral","risk_flags":["router_unparsed_response"],"review_required":True,"raw_response":response}

    def classify_event(self, prompt):
        if not self.is_configured():
            return {"event_type":"unknown","summary":"llm_router_not_configured","sentiment_score":0.0,"impact_horizon":"intraday","affected_assets":[],"market_regime_bias":"neutral","risk_flags":["llm_router_not_configured"],"review_required":True}
        response = http_post_json(self.endpoint, self.build_payload(prompt), headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.timeout_seconds)
        return self.parse_response(response)
