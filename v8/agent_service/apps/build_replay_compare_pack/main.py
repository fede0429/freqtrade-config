from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
AUDIT_DIR = ROOT / "user_data/agent_runtime/audit"
OUT_DIR = ROOT / "v8/agent_service/reports"
TRACE_FILES = [
    "stake_decision_trace.jsonl",
    "stake_apply_trace.jsonl",
    "exit_shadow_trace.jsonl",
    "exit_apply_trace.jsonl",
    "stoploss_shadow_trace.jsonl",
    "stoploss_apply_trace.jsonl",
    "entry_confirm_trace.jsonl",
    "entry_confirm_apply_trace.jsonl",
    "roi_shadow_trace.jsonl",
    "roi_apply_trace.jsonl",
]


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def main():
    summary = {}
    for name in TRACE_FILES:
        rows = load_jsonl(AUDIT_DIR / name)
        summary[name] = {
            "count": len(rows),
            "sample": rows[-3:] if rows else [],
        }

    pack = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "replay_compare_pack",
        "summary": summary,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "replay_compare_pack.json"
    out.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
