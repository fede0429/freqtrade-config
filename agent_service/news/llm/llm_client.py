import json
import os
import urllib.request

class LLMClient:
    def __init__(self, endpoint=None, api_key=None, model=None, timeout_seconds=30):
        self.endpoint = endpoint or os.getenv("NEWS_LLM_API_ENDPOINT", "")
        self.api_key = api_key or os.getenv("NEWS_LLM_API_KEY", "")
        self.model = model or os.getenv("NEWS_LLM_MODEL", "")
        self.timeout_seconds = timeout_seconds

    def is_configured(self):
        return bool(self.endpoint and self.api_key and self.model)

    def classify_event(self, title, body, source_name):
        payload = {
            "task": "classify_news_event",
            "source_name": source_name,
            "title": title,
            "body": body,
            "instructions": {
                "return_format": "json_only",
                "fields": [
                    "event_type", "summary", "sentiment_score", "impact_horizon",
                    "affected_assets", "market_regime_bias", "risk_flags", "review_required"
                ]
            }
        }
        return self._post_json(payload)

    def _post_json(self, payload):
        if not self.is_configured():
            return {
                "event_type": "unknown",
                "summary": "llm_not_configured",
                "sentiment_score": 0.0,
                "impact_horizon": "intraday",
                "affected_assets": [],
                "market_regime_bias": "neutral",
                "risk_flags": ["llm_not_configured"],
                "review_required": True,
            }
        body = json.dumps({"model": self.model, "input": payload}).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))
