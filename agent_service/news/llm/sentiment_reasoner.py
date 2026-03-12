from agent_service.news.llm.llm_client import LLMClient

class SentimentReasoner:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze(self, title, body, source_name):
        return self.llm_client.classify_event(title=title, body=body, source_name=source_name)
