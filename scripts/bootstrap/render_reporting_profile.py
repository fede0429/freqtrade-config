#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import os


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def resolve_runtime_paths(payload: dict) -> dict:
    input_source = payload.setdefault('input_source', {})
    paths = payload.setdefault('paths', {})
    if input_source.get('type') == 'sqlite':
        override_key = 'PAPER_TRADES_DB_PATH' if payload.get('profile_name') == 'paper' else 'PROD_TRADES_DB_PATH'
        resolved = os.environ.get(override_key) or os.environ.get('TRADES_DB_PATH') or input_source.get('db_path') or paths.get('pnl_input')
        if resolved:
            input_source['db_path'] = resolved
            paths['pnl_input'] = resolved
    return payload


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: render_reporting_profile.py <market> <env> <output>')
        return 1
    market, env, output = sys.argv[1:4]
    root = Path(__file__).resolve().parents[2]
    merged = deep_merge(load(root / 'config' / 'reporting' / 'base' / 'common.json'), load(root / 'config' / 'reporting' / 'base' / f'{market}.json'))
    merged = deep_merge(merged, load(root / 'config' / 'reporting' / 'env' / f'{env}.json'))
    merged = resolve_runtime_paths(merged)
    Path(output).write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'[OK] wrote {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
