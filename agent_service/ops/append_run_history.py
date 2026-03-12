import json
from pathlib import Path
def append_run_history(payload, output_path="agent_service/reports/run_history.jsonl"):
    out = Path(output_path); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f: f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return out
