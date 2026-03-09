#!/usr/bin/env python3
import json, sys
from pathlib import Path

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main(argv):
    if len(argv) != 2:
        print('Usage: validate_config_governance.py <config.json>')
        return 2
    path = Path(argv[1])
    cfg = load(path)
    errors = []
    warnings = []

    mode = cfg.get('pair_selection_mode')
    pairlists = cfg.get('pairlists', [])
    whitelist = cfg.get('exchange', {}).get('pair_whitelist', [])
    methods = [p.get('method') for p in pairlists if isinstance(p, dict)]

    if mode not in {'static', 'dynamic'}:
        errors.append('pair_selection_mode must be static or dynamic')
    if mode == 'static' and 'StaticPairList' not in methods:
        errors.append('static mode requires pairlists to include StaticPairList')
    if mode == 'static' and not whitelist:
        errors.append('static mode requires exchange.pair_whitelist to be non-empty')
    if mode == 'dynamic' and 'VolumePairList' not in methods:
        errors.append('dynamic mode requires VolumePairList')
    if mode == 'dynamic' and whitelist:
        warnings.append('dynamic mode should usually leave exchange.pair_whitelist empty')

    for field in ['key', 'secret']:
        val = cfg.get('exchange', {}).get(field)
        if val and str(val).startswith('CHANGE_ME'):
            warnings.append(f'exchange.{field} still uses placeholder; expected docker env override')

    api = cfg.get('api_server', {})
    for k in ['username', 'password', 'jwt_secret_key']:
        val = api.get(k)
        if val and str(val).startswith('CHANGE_ME'):
            warnings.append(f'api_server.{k} still uses placeholder; expected docker env override')

    print(f'Config: {path}')
    if errors:
        print('ERRORS:')
        for e in errors:
            print(f' - {e}')
    if warnings:
        print('WARNINGS:')
        for w in warnings:
            print(f' - {w}')
    if not errors and not warnings:
        print('[OK] configuration governance checks passed')
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
