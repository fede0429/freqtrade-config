#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution.trade_reconciliation import reconcile_execution_trades
from services.execution.trace import build_run_id


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Reconcile filled execution orders with real trade records.')
    p.add_argument('--profile', required=True)
    p.add_argument('--as-of-date', default=None)
    p.add_argument('--limit', type=int, default=100)
    p.add_argument('--tolerance-minutes', type=int, default=24 * 60)
    return p.parse_args()


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    args = parse_args()
    profile = load_json(args.profile)
    summary = reconcile_execution_trades(
        execution_db_path=profile['paths']['execution_state_db'],
        trades_db_path=profile['paths']['trades_db'],
        as_of_date=args.as_of_date,
        tolerance_minutes=args.tolerance_minutes,
        limit=args.limit,
        run_id=build_run_id('reconcile'),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
