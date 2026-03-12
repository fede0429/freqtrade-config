class MacroReasoner:
    def __init__(self, llm_client): self.llm_client = llm_client
    def analyze(self, title, body, source_name):
        result = self.llm_client.classify_event(title=title, body=body, source_name=source_name)
        result.setdefault("macro_tag", "unclassified")
        return result
