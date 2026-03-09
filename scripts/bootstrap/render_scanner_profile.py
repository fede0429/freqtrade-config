#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from copy import deepcopy


def deep_merge(base, override):
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: render_scanner_profile.py <market> <env> <output>')
        return 1
    market, env, output = sys.argv[1:4]
    root = Path(__file__).resolve().parents[2]
    common = json.loads((root / 'config/scanner/base/common.json').read_text())
    market_cfg = json.loads((root / f'config/scanner/base/{market}.json').read_text())
    env_cfg = json.loads((root / f'config/scanner/env/{env}.json').read_text())
    rendered = deep_merge(common, market_cfg)
    rendered = deep_merge(rendered, env_cfg)
    rendered['profile_name'] = rendered.get('profile_name', env)
    rendered['market'] = market
    out_path = root / output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rendered, indent=2) + '\n')
    print(out_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
