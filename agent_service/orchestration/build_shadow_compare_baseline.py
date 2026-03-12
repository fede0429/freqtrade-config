import json
from pathlib import Path

DECISION_CACHE_PATH = "user_data/agent_runtime/state/decision_cache.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    decision_cache = load_json(DECISION_CACHE_PATH, {"pairs": {}})
    payload = {"schema_version":"1.0","kind":"shadow_compare_baseline","pairs": {}}
    for pair, meta in decision_cache.get("pairs", {}).items():
        payload["pairs"][pair] = {"confidence": meta.get("confidence"), "governance_gate": meta.get("governance_gate"), "trading_mode": meta.get("trading_mode"), "entry_allowed": meta.get("entry_allowed"), "stake_multiplier": meta.get("stake_multiplier"), "target_rr": meta.get("target_rr"), "news_governance": meta.get("news_governance")}
    out = Path("agent_service/reports/shadow_compare_baseline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
