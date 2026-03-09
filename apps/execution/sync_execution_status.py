#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution.execution_store import ExecutionStore
from services.execution.lifecycle_manager import classify_error_category
from services.execution.real_connector import build_connector
from services.execution.trace import build_run_id, build_trace_context


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Sync execution order lifecycle back into execution store.')
    p.add_argument('--profile', required=True)
    p.add_argument('--limit', type=int, default=100)
    return p.parse_args()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def calc_slippage_bps(requested_price: float | None, fill_price: float | None, side: str) -> float | None:
    if not requested_price or not fill_price or requested_price <= 0:
        return None
    raw = (fill_price - requested_price) / requested_price * 10000.0
    if str(side).lower() == 'short':
        raw = -raw
    return round(raw, 4)


def main() -> int:
    args = parse_args()
    profile = load_json(args.profile)
    store = ExecutionStore(profile['paths']['execution_state_db'])
    connector = build_connector(profile)
    orders = store.list_open_orders(limit=args.limit)
    run_id = build_run_id('sync')

    summary = {'run_id': run_id, 'processed': 0, 'filled': 0, 'accepted': 0, 'partial': 0, 'failed': 0, 'cancelled': 0, 'unchanged': 0, 'results': []}
    for order in orders:
        trace = build_trace_context(stage='status_sync', run_id=run_id, parent_trace_id=order.get('trace_id'), seed=order['order_id'])
        try:
            status = connector.fetch_order_status(order, profile)
            slippage_bps = calc_slippage_bps(order.get('requested_price'), status.average_fill_price, order.get('side', 'long'))
            raw_response = status.raw_response or {}
            error_category = classify_error_category({'order_status': status.order_status, 'last_error': status.last_error, 'error_category': order.get('error_category')})
            store.mark_status(
                order['order_id'],
                order_status=status.order_status,
                dispatch_status='filled' if status.order_status == 'filled' else order.get('dispatch_status'),
                venue_order_id=status.venue_order_id,
                external_order_id=raw_response.get('external_order_id') or raw_response.get('client_order_id'),
                average_fill_price=status.average_fill_price,
                executed_quantity=status.executed_quantity,
                fee_amount=status.fee_amount,
                slippage_bps=slippage_bps,
                last_error=status.last_error,
                error_category=error_category,
                raw_response_json=json.dumps(raw_response, ensure_ascii=False) if status.raw_response is not None else None,
                accepted_at=order.get('accepted_at') or (order.get('updated_at') if status.order_status in {'accepted', 'partial'} else None),
                filled_at=status.filled_at,
                cancelled_at=status.cancelled_at,
                run_id=trace.run_id,
                trace_id=trace.trace_id,
                parent_trace_id=trace.parent_trace_id,
            )
            summary['processed'] += 1
            bucket = status.order_status if status.order_status in {'filled', 'accepted', 'partial', 'failed', 'cancelled'} else 'unchanged'
            summary[bucket] = summary.get(bucket, 0) + 1
            summary['results'].append({'order_id': order['order_id'], 'status': status.order_status, 'trace_id': trace.trace_id, 'remote_id': status.remote_id, 'venue_order_id': status.venue_order_id, 'fill_price': status.average_fill_price, 'fee_amount': status.fee_amount, 'error_category': error_category})
        except Exception as exc:  # pragma: no cover
            summary['failed'] += 1
            summary['results'].append({'order_id': order['order_id'], 'status': 'error', 'trace_id': trace.trace_id, 'message': str(exc)})

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
