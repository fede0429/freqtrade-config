import json
from pathlib import Path
from agent_service.calibration.calibration_config import load_calibration_config
from agent_service.calibration.build_calibration_report import write_calibration_report

DECISION_CACHE_PATH = "user_data/agent_runtime/state/decision_cache.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    cfg = load_calibration_config()
    decision_cache = load_json(DECISION_CACHE_PATH, {"pairs": {}})
    results = []
    for entry_conf in cfg.get("entry_confidence_grid", []):
        for news_cred in cfg.get("news_min_credibility_grid", []):
            for stake_cap in cfg.get("stake_multiplier_caps", []):
                score = 0; review_pairs = 0; blocked_pairs = 0
                for _, meta in decision_cache.get("pairs", {}).items():
                    confidence = float(meta.get("confidence", 0.0))
                    gov = str(meta.get("governance_gate", "passed"))
                    if gov != "passed": blocked_pairs += 1
                    if str(meta.get("trading_mode")) == "review_shadow": review_pairs += 1
                    if confidence >= float(entry_conf): score += 1
                results.append({"entry_confidence": entry_conf, "news_min_credibility": news_cred, "stake_multiplier_cap": stake_cap, "score": score, "blocked_pairs": blocked_pairs, "review_pairs": review_pairs})
    best = sorted(results, key=lambda x: (x["score"], -x["blocked_pairs"], -x["review_pairs"]), reverse=True)[:10]
    out = write_calibration_report({"mode": cfg.get("mode","shadow"), "search_space_size": len(results), "top_candidates": best})
    print(out)

if __name__ == "__main__":
    main()
