import json
from pathlib import Path

HISTORY_PATH = "agent_service/reports/run_history.jsonl"

def load_jsonl(path):
    p = Path(path)
    if not p.exists(): return []
    rows = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except Exception: continue
    return rows

def main():
    rows = load_jsonl(HISTORY_PATH)
    payload = {"kind":"weekly_ops_summary","total_runs": len(rows), "ok_runs": sum(1 for row in rows if row.get("shadow_run_status") == "ok"), "degraded_runs": sum(1 for row in rows if row.get("shadow_run_status") != "ok"), "runtime_readiness_ok_runs": sum(1 for row in rows if row.get("runtime_readiness_status") == "ok"), "latest_runs": rows[-10:]}
    out = Path("agent_service/reports/weekly_ops_summary.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
