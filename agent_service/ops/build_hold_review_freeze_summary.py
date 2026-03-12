import json
from pathlib import Path

DECISION_PANEL_PATH = "agent_service/reports/promote_hold_decision_panel.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    panel = load_json(DECISION_PANEL_PATH, {"hold_pairs": [], "review_pairs": []})
    payload = {"kind":"hold_review_freeze_summary","hold_count": len(panel.get("hold_pairs", [])), "review_count": len(panel.get("review_pairs", [])), "freeze_like_pairs": [row for row in panel.get("hold_pairs", []) if "governance_blocked" in row.get("reasons", [])]}
    out = Path("agent_service/reports/hold_review_freeze_summary.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
