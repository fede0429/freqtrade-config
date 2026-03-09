#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_STAGES = {"candidate", "dry_run", "canary", "production", "retired"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    return 1


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    registry_path = root / "strategies" / "registry" / "strategy_registry.json"
    registry = load_json(registry_path)
    names: set[str] = set()

    for item in registry["strategies"]:
        name = item["name"]
        if name in names:
            return fail(f"duplicate strategy name: {name}")
        names.add(name)

        if item["lifecycle_stage"] not in ALLOWED_STAGES:
            return fail(f"invalid lifecycle stage for {name}: {item['lifecycle_stage']}")

        code_path = root / item["code_path"]
        params_root = root / item["params_path"]
        if not code_path.exists():
            return fail(f"missing code path for {name}: {code_path}")
        if not params_root.exists():
            return fail(f"missing params path for {name}: {params_root}")
        for filename in ("base.json", "paper.json", "prod.json"):
            target = params_root / filename
            if not target.exists():
                return fail(f"missing {filename} for {name}")
            payload = load_json(target)
            if filename == "prod.json" and item["lifecycle_stage"] == "candidate" and payload.get("risk_budget_fraction", 0) != 0:
                return fail(f"candidate strategy {name} must have zero prod risk budget")

        gate = item["upgrade_gate"]
        required_gate_keys = {
            "required_backtest_days",
            "max_backtest_drawdown",
            "min_profit_factor",
            "min_win_rate",
            "dry_run_days",
            "canary_days",
        }
        missing = sorted(required_gate_keys - set(gate.keys()))
        if missing:
            return fail(f"missing upgrade gate keys for {name}: {', '.join(missing)}")

    profile_dir = root / "strategies" / "profiles"
    for profile_name in ("candidate.json", "dry_run.json", "canary.json", "production.json"):
        profile = load_json(profile_dir / profile_name)
        for strategy_name in profile["allowed_strategies"]:
            if strategy_name not in names:
                return fail(f"profile {profile_name} references unknown strategy {strategy_name}")

    print(f"[OK] validated {len(names)} strategies from {registry_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
