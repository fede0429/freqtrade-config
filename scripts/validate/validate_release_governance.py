#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path
REQUIRED = ['schema_version', 'release_name', 'timezone', 'release', 'checks', 'paths', 'market_type', 'profile_name', 'release_channel']
PATH_KEYS = ['strategy_manifest', 'scanner_report', 'daily_report', 'risk_profile', 'reporting_profile', 'trading_config', 'docker_compose']

def main() -> int:
    if len(sys.argv) != 2:
        print('usage: validate_release_governance.py <profile.json>')
        return 1
    data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        print(f'validation failed: missing keys {missing}')
        return 2
    for key in PATH_KEYS:
        if key not in data['paths']:
            print(f'validation failed: paths.{key} missing')
            return 3
    print(f'[OK] release governance valid: {sys.argv[1]}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
