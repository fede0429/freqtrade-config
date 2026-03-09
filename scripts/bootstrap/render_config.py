#!/usr/bin/env python3
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main(argv):
    if len(argv) != 5:
        print('Usage: render_config.py <spot|futures> <dev|paper|prod> <static|dynamic> <output_path>')
        return 2

    market, env_name, pair_mode, output_path = argv[1:]
    if market not in {'spot', 'futures'}:
        raise SystemExit('market must be spot or futures')
    if env_name not in {'dev', 'paper', 'prod'}:
        raise SystemExit('env must be dev, paper, or prod')
    if pair_mode not in {'static', 'dynamic'}:
        raise SystemExit('pair_mode must be static or dynamic')

    config = {}
    for rel in [
        'config/base/common.json',
        f'config/base/{market}.json',
        f'config/env/{env_name}.json',
        f'config/pairlists/{market}.{pair_mode}.json',
    ]:
        config = deep_merge(config, load_json(ROOT / rel))

    out = ROOT / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'[OK] wrote {out}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
