from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
INPUT_PATH = ROOT / "agent_service/reports/latest_agent_signals.json"
OUTPUT_PATH = ROOT / "user_data/agent_runtime/state/decision_cache.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_input() -> dict:
    if not INPUT_PATH.exists():
        return {"signals": []}
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {"signals": []}


def source_timestamp(payload: dict) -> str | None:
    source_ts = payload.get("ts")
    return source_ts if isinstance(source_ts, str) and source_ts else None


def cache_ts_mode(payload: dict) -> str:
    mode = str(payload.get("cache_ts_mode", "source")).lower()
    return "build" if mode == "build" else "source"


def transform(payload: dict) -> dict:
    pairs = {}
    for item in payload.get("signals", []):
        pair = str(item.get("pair", "")).upper()
        if not pair:
            continue
        pairs[pair] = {
            "agent_enabled": bool(item.get("agent_enabled", True)),
            "confidence": float(item.get("confidence", 0.0)),
            "stake_multiplier": float(item.get("stake_multiplier", 1.0)),
            "entry_allowed": bool(item.get("entry_allowed", True)),
            "exit_signal": bool(item.get("exit_signal", False)),
            "exit_reason": item.get("exit_reason"),
            "stoploss_mode": item.get("stoploss_mode", "tighten_only"),
            "agent_stoploss": item.get("agent_stoploss"),
            "target_rr": item.get("target_rr"),
            "target_profit_ratio": item.get("target_profit_ratio"),
            "governance_gate": item.get("governance_gate", "blocked"),
        }

    built_at = utc_now()
    return {
        "ts": source_timestamp(payload) or built_at,
        "built_at": built_at,
        "cache_ts_mode": cache_ts_mode(payload),
        "source": payload.get("source", "build_decision_cache"),
        "pairs": pairs,
    }


def main():
    payload = load_input()
    cache = transform(payload)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
