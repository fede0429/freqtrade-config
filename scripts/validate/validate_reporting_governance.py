#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json

REQUIRED = ['schema_version', 'timezone', 'reporting', 'paths', 'market_type', 'profile_name']
FORBIDDEN_SAMPLE_MARKERS = ('fixtures', 'sample', 'mock')


def _looks_like_fixture(path_value: str) -> bool:
    lowered = path_value.lower()
    return any(marker in lowered for marker in FORBIDDEN_SAMPLE_MARKERS)


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: validate_reporting_governance.py <profile.json>')
        return 1
    profile_path = Path(sys.argv[1])
    data = json.loads(profile_path.read_text(encoding='utf-8'))
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        print(f'validation failed: missing keys {missing}')
        return 2
    for key in ['scanner_report', 'strategy_manifest', 'risk_profile', 'output_dir', 'pnl_input']:
        if key not in data['paths']:
            print(f'validation failed: paths.{key} missing')
            return 3
    input_source = data.get('input_source', {'type': 'json'})
    source_type = input_source.get('type', 'json')
    if source_type not in {'json', 'sqlite'}:
        print(f'validation failed: unsupported input_source.type {source_type}')
        return 4
    if source_type == 'sqlite':
        for key in ['db_path', 'as_of_date', 'equity_start']:
            if key not in input_source:
                print(f'validation failed: input_source.{key} missing for sqlite mode')
                return 5
        db_path = str(input_source['db_path'])
        profile_name = data.get('profile_name', '')
        if profile_name == 'prod' and _looks_like_fixture(db_path):
            print(f'validation failed: prod profile cannot point to fixture/sample db_path: {db_path}')
            return 6
        if profile_name == 'paper' and _looks_like_fixture(db_path):
            print(f'[WARN] paper profile still points to fixture/sample db_path: {db_path}')
    print(f'[OK] reporting governance valid: {profile_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
