from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def write_approval_summary_report(
    approval_summary: Dict[str, Any],
    output_path: str = "agent_service/reports/approval_summary_report.json",
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(approval_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
