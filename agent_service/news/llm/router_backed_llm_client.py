from agent_service.integration.llm_provider_router import LLMProviderRouter

class RouterBackedLLMClient:
    def __init__(self): self.router = LLMProviderRouter()
    def classify_event(self, title, body, source_name):
        prompt = {"task":"classify_news_event","source_name":source_name,"title":title,"body":body,"instructions":{"return_format":"json_only","fields":["event_type","summary","sentiment_score","impact_horizon","affected_assets","market_regime_bias","risk_flags","review_required"]}}
        return self.router.classify_event(prompt)
