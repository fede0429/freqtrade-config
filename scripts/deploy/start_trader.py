#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from services.execution.startup_gate import StartupGate


def main() -> int:
    parser = argparse.ArgumentParser(description='Run preflight and arm trader startup only if checks pass.')
    parser.add_argument('release_profile', help='Path to release runtime profile JSON')
    parser.add_argument('--execute', action='store_true', help='Actually run docker compose up after preflight passes')
    parser.add_argument('--allow-hold', action='store_true', help='Still emit startup bundle even if startup is blocked')
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    profile_path = Path(args.release_profile)
    if not profile_path.is_absolute():
        profile_path = (root / profile_path).resolve()

    gate = StartupGate(profile_path)
    decision, preflight_path = gate.run_preflight()
    approved = bool(decision.get('approved', False))

    bundle = gate.build_bundle(preflight_path=preflight_path, approved=approved)
    bundle_path = gate.write_bundle(bundle)

    print(json.dumps({
        'preflight_report': str(preflight_path.relative_to(root)) if preflight_path.is_relative_to(root) else str(preflight_path),
        'startup_bundle': str(bundle_path.relative_to(root)) if bundle_path.is_relative_to(root) else str(bundle_path),
        'approved': approved,
        'startup_mode': bundle.startup_mode,
        'command_preview': bundle.command_preview,
    }, indent=2, ensure_ascii=False))

    if not approved:
        if args.allow_hold:
            return 0
        return 2

    if args.execute:
        import subprocess
        result = subprocess.run(bundle.command_preview, cwd=root)
        return int(result.returncode)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
