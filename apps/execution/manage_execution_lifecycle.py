#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution.execution_store import ExecutionStore, build_execution_order_record
from services.execution.idempotency import ExecutionIdempotencyStore
from services.execution.lifecycle_manager import classify_error_category, should_replace_order
from services.execution.real_connector import ExecutionDispatchRequest, build_connector
from services.execution.trace import build_run_id, build_trace_context


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Retry/cancel-replace failed or partial execution orders.')
    p.add_argument('--profile', required=True)
    p.add_argument('--limit', type=int, default=100)
    return p.parse_args()


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    args = parse_args()
    profile = load_json(args.profile)
    store = ExecutionStore(profile['paths']['execution_state_db'])
    idem = ExecutionIdempotencyStore(profile['paths']['execution_state_db'])
    connector = build_connector(profile)
    candidates = store.list_retriable_orders(limit=args.limit)
    run_id = build_run_id('lifecycle')
    summary = {'run_id': run_id, 'considered': len(candidates), 'replaced': 0, 'deduplicated': 0, 'skipped': 0, 'by_error_category': {}, 'results': []}
    for order in candidates:
        category = classify_error_category(order)
        plan = should_replace_order(order, profile)
        if not plan:
            summary['skipped'] += 1
            summary['by_error_category'][category] = summary['by_error_category'].get(category, 0) + 1
            continue
        trace = build_trace_context(stage='lifecycle_replace', run_id=run_id, parent_trace_id=order.get('trace_id'), seed=order['order_id'])
        req = ExecutionDispatchRequest(
            decision_id=order['decision_id'],
            signal_id=order['signal_id'],
            strategy_name=order['strategy_name'],
            pair=order['pair'],
            side=order['side'],
            action=order['action'],
            order_type=order['order_type'],
            stake_fraction=float(order.get('requested_stake_fraction') or 0.0),
            entry_price=order.get('requested_price'),
            metadata={
                'dispatch_kind': 'replace',
                'parent_order_id': order['order_id'],
                'replace_reason': plan.replace_reason,
                'retry_count': plan.next_retry_count,
                'requested_quantity': plan.requested_quantity,
                'requested_notional': plan.requested_notional,
                'error_category': plan.error_category,
                'run_id': trace.run_id,
                'trace_id': trace.trace_id,
            },
        )
        payload = req.to_payload()
        req_hash = idem.build_request_hash(payload)
        if idem.get_existing_by_request_hash(order['decision_id'], req_hash):
            summary['deduplicated'] += 1
            summary['results'].append({'source_order_id': order['order_id'], 'status': 'deduplicated', 'trace_id': trace.trace_id, 'error_category': category})
            continue
        result = connector.dispatch(req)
        response_payload = result.response_payload or {}
        new_order_id = f"{order['order_id']}:r{plan.next_retry_count}"
        store.upsert_order(build_execution_order_record(
            order_id=new_order_id,
            decision_id=order['decision_id'],
            signal_id=order['signal_id'],
            strategy_name=order['strategy_name'],
            pair=order['pair'],
            side=order['side'],
            action=order['action'],
            order_type=order['order_type'],
            requested_price=float(order['requested_price']) if order.get('requested_price') is not None else None,
            requested_stake_fraction=float(order.get('requested_stake_fraction') or 0.0),
            requested_notional=plan.requested_notional,
            requested_quantity=plan.requested_quantity,
            dispatch_status=result.status,
            remote_id=result.remote_id,
            external_order_id=response_payload.get('external_order_id') or response_payload.get('client_order_id'),
            connector_mode=connector.mode,
            raw_response_json=json.dumps(response_payload, ensure_ascii=False) if response_payload is not None else None,
            retry_count=plan.next_retry_count,
            parent_order_id=order['order_id'],
            replace_reason=plan.replace_reason,
            error_category=plan.error_category,
            last_error=order.get('last_error'),
            run_id=trace.run_id,
            trace_id=trace.trace_id,
            parent_trace_id=trace.parent_trace_id,
        ))
        idem.record_dispatch(
            decision_id=order['decision_id'],
            signal_id=order['signal_id'],
            action=order['action'],
            pair=order['pair'],
            strategy_name=order['strategy_name'],
            request_hash=req_hash,
            dispatch_status=result.status,
            remote_id=result.remote_id,
            response_payload=result.response_payload,
            order_id=new_order_id,
            run_id=trace.run_id,
            trace_id=trace.trace_id,
            parent_trace_id=trace.parent_trace_id,
        )
        summary['replaced'] += 1
        summary['by_error_category'][plan.error_category] = summary['by_error_category'].get(plan.error_category, 0) + 1
        summary['results'].append({'source_order_id': order['order_id'], 'new_order_id': new_order_id, 'status': result.status, 'trace_id': trace.trace_id, 'error_category': plan.error_category})
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
