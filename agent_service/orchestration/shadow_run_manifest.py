import json
from pathlib import Path
def write_shadow_run_manifest(payload, output_path="agent_service/reports/shadow_run_manifest.json"):
    out = Path(output_path); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); return out
