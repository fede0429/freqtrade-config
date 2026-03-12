import json
from pathlib import Path
def write_news_aggregation_report(payload, output_path="agent_service/reports/news_aggregation_report.json"):
    out = Path(output_path); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
