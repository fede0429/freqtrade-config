#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_TOP = ['market', 'profile_name', 'selection', 'pair_filters', 'market_regime', 'output']


def validate(payload):
    for key in REQUIRED_TOP:
        if key not in payload:
            raise ValueError(f'missing key: {key}')
    min_score = payload['selection']['min_score']
    watchlist_score = payload['selection']['watchlist_min_score']
    if not (0 <= watchlist_score <= min_score <= 100):
        raise ValueError('invalid score thresholds')
    if payload['pair_filters']['min_liquidity_usd'] <= 0:
        raise ValueError('min_liquidity_usd must be positive')
    if payload['pair_filters']['max_volatility_pct'] <= 0:
        raise ValueError('max_volatility_pct must be positive')
    if payload['market_regime']['risk_off_breadth_threshold'] >= payload['market_regime']['trend_breadth_threshold']:
        raise ValueError('risk_off threshold must be below trend threshold')


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: validate_scanner_governance.py <profile.json>')
        return 1
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text())
    validate(payload)
    print(f'validated {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
