import json
from pathlib import Path

DECISION_PANEL_PATH = "agent_service/reports/promote_hold_decision_panel.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    panel = load_json(DECISION_PANEL_PATH, {"promote_candidates": []})
    payload = {"kind":"pair_promotion_candidates", "count": len(panel.get("promote_candidates", [])), "items": panel.get("promote_candidates", [])}
    out = Path("agent_service/reports/pair_promotion_candidates.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
