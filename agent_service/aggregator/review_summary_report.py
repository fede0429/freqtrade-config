from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def write_review_summary_report(
    summary: Dict[str, Any],
    output_path: str = "agent_service/reports/review_summary_report.json",
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
