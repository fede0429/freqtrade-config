import json
from pathlib import Path

class NewsReviewQueue:
    def __init__(self, output_path="agent_service/reports/news_review_queue.json"):
        self.output_path = Path(output_path)
    def write(self, payload):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.output_path
