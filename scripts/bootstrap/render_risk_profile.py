#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def deep_merge(base, override):
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def main(argv):
    if len(argv) != 4:
        print('Usage: render_risk_profile.py <spot|futures> <dev|paper|prod> <output_path>')
        return 2

    market, env_name, output_path = argv[1:]
    if market not in {'spot', 'futures'}:
        raise SystemExit('market must be spot or futures')
    if env_name not in {'dev', 'paper', 'prod'}:
        raise SystemExit('env must be dev, paper, or prod')

    profile = {}
    for rel in [
        'config/risk/base/common.json',
        f'config/risk/base/{market}.json',
        f'config/risk/env/{env_name}.json',
    ]:
        profile = deep_merge(profile, load_json(ROOT / rel))

    profile['market_type'] = market
    profile['environment'] = env_name

    out = ROOT / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as handle:
        json.dump(profile, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print(f'[OK] wrote {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
