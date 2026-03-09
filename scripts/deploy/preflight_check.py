#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from services.execution.release_planner import ReleasePlanner
from services.execution.release_loader import load_json


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: preflight_check.py <release_profile.json>')
        return 1
    profile_path = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parents[2]
    profile = load_json(profile_path)
    decision = ReleasePlanner(profile).evaluate()
    payload = decision.to_dict()
    payload['generated_at'] = datetime.now(timezone.utc).isoformat()
    payload['profile_path'] = str(profile_path.relative_to(root)) if profile_path.is_relative_to(root) else str(profile_path)
    output_dir = root / profile['release']['preflight_output_dir']
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"preflight_{profile['market_type']}_{profile['profile_name']}.json"
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(output_path)
    return 0 if decision.approved else 2

if __name__ == '__main__':
    raise SystemExit(main())
