#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

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

def main() -> int:
    if len(sys.argv) != 4:
        print('usage: render_release_profile.py <market> <env> <output>')
        return 1
    market, env, output = sys.argv[1:4]
    root = Path(__file__).resolve().parents[2]
    merged = deep_merge(load(root / 'config' / 'release' / 'base' / 'common.json'), load(root / 'config' / 'release' / 'base' / f'{market}.json'))
    merged = deep_merge(merged, load(root / 'config' / 'release' / 'env' / f'{env}.json'))
    Path(output).write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'[OK] wrote {output}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
