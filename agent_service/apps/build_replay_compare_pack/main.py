from __future__ import annotations
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = ROOT / "user_data/agent_runtime/audit"
STATE_DIR = ROOT / "user_data/agent_runtime/state"
CURRENT_RUN_ID_FILE = STATE_DIR / "current_run_id.txt"
OUT_DIR = ROOT / "agent_service/reports"
RUN_ID_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")
TRACE_FILES = [
    "bridge_runtime_trace.jsonl",
    "stake_decision_trace.jsonl",
    "stake_fallback_trace.jsonl",
    "stake_apply_trace.jsonl",
    "exit_shadow_trace.jsonl",
    "exit_skip_trace.jsonl",
    "exit_apply_trace.jsonl",
    "stoploss_shadow_trace.jsonl",
    "stoploss_skip_trace.jsonl",
    "stoploss_apply_trace.jsonl",
    "entry_confirm_trace.jsonl",
    "entry_confirm_skip_trace.jsonl",
    "entry_confirm_block_trace.jsonl",
    "entry_confirm_apply_trace.jsonl",
    "roi_shadow_trace.jsonl",
    "roi_skip_trace.jsonl",
    "roi_apply_trace.jsonl",
]


def sanitize_run_id(value: str) -> str:
    cleaned = RUN_ID_PATTERN.sub("-", value).strip("-._")
    return cleaned


def resolve_run_id() -> str:
    env_value = os.environ.get("AGENT_RUN_ID", "").strip()
    if env_value:
        return sanitize_run_id(env_value)
    if CURRENT_RUN_ID_FILE.exists():
        file_value = CURRENT_RUN_ID_FILE.read_text(encoding="utf-8-sig").strip()
        if file_value:
            return sanitize_run_id(file_value)
    return ""


def available_run_ids() -> list[str]:
    if not AUDIT_ROOT.exists():
        return []
    return sorted(path.name for path in AUDIT_ROOT.iterdir() if path.is_dir())


def resolve_audit_dir(run_id: str) -> Path:
    return AUDIT_ROOT / run_id


def require_run_context(run_id: str, audit_dir: Path) -> None:
    if not run_id:
        known_runs = available_run_ids()
        hint = ", ".join(known_runs[-5:]) if known_runs else "none"
        raise SystemExit(
            f"No active AGENT_RUN_ID found. Set AGENT_RUN_ID or write {CURRENT_RUN_ID_FILE}. Available audit runs: {hint}"
        )
    if not audit_dir.exists():
        raise SystemExit(f"Audit directory for run_id '{run_id}' not found: {audit_dir}")


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
    run_id = resolve_run_id()
    audit_dir = resolve_audit_dir(run_id)
    require_run_context(run_id, audit_dir)

    summary = {}
    for name in TRACE_FILES:
        rows = load_jsonl(audit_dir / name)
        summary[name] = {"count": len(rows), "sample": rows[-5:] if rows else []}

    pack = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "replay_compare_pack",
        "run_id": run_id,
        "audit_dir": str(audit_dir.relative_to(ROOT)),
        "summary": summary,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(pack, indent=2, ensure_ascii=False)
    latest_out = OUT_DIR / "replay_compare_pack.json"
    latest_out.write_text(payload, encoding="utf-8")
    scoped_out = OUT_DIR / f"replay_compare_pack_{run_id}.json"
    scoped_out.write_text(payload, encoding="utf-8")
    print(scoped_out)


if __name__ == "__main__":
    main()