#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.scanner.market_data import load_fixture_metrics


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: validate_scanner_data_source.py <fixture.json>')
        return 1
    path = Path(sys.argv[1])
    metrics = load_fixture_metrics(path)
    if not metrics:
        raise SystemExit('fixture produced zero metrics')
    required = {'pair', 'liquidity_usd', 'volume_ratio', 'momentum_24h', 'momentum_1h', 'volatility'}
    for item in metrics:
        missing = required - set(item.keys())
        if missing:
            raise SystemExit(f"{item.get('pair', '?')}: missing keys {sorted(missing)}")
    print(json.dumps({'fixture': str(path), 'pairs': len(metrics), 'status': 'ok'}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
