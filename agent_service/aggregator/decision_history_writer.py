from __future__ import annotations

from pathlib import Path
import json
from typing import Dict, Any


def append_decision_history(decision_cache: Dict[str, Any], output_path: str = "agent_service/reports/decision_history.jsonl") -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": decision_cache.get("ts"),
        "schema_version": decision_cache.get("schema_version"),
        "source": decision_cache.get("source"),
        "pairs": {
            pair: {
                "confidence": meta.get("confidence"),
                "risk_score": meta.get("risk_score"),
                "market_regime": meta.get("market_regime"),
                "agent_enabled": meta.get("agent_enabled"),
                "entry_allowed": meta.get("entry_allowed"),
                "stake_multiplier": meta.get("stake_multiplier"),
                "target_rr": meta.get("target_rr"),
                "anomaly_guard": meta.get("anomaly_guard"),
                "execution_policy": meta.get("execution_policy"),
            }
            for pair, meta in decision_cache.get("pairs", {}).items()
        },
    }
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return out
