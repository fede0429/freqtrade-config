#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution.idempotency import ExecutionIdempotencyStore
from services.execution.execution_store import ExecutionStore, build_execution_order_record
from services.execution.real_connector import ExecutionDispatchRequest, build_connector
from services.execution.trace import build_run_id, build_trace_context


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Dispatch approved meta decisions to execution connector with idempotency.')
    p.add_argument('--profile', required=True)
    p.add_argument('--db-path', default=None, help='Signal pipeline sqlite path. Overrides profile path.')
    p.add_argument('--limit', type=int, default=50)
    return p.parse_args()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_dispatch_candidates(db_path: Path, limit: int) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        query = '''
        SELECT
            d.decision_id,
            d.signal_id,
            COALESCE(d.action, 'accept') AS action,
            COALESCE(d.allocated_risk_fraction, 0.0) AS allocated_risk_fraction,
            COALESCE(d.allocated_notional, 0.0) AS allocated_notional,
            COALESCE(s.strategy_name, 'unknown') AS strategy_name,
            COALESCE(s.pair, 'unknown') AS pair,
            COALESCE(s.side, 'long') AS side,
            s.entry_price
        FROM decision_events d
        JOIN strategy_signals s ON s.signal_id = d.signal_id
        WHERE d.action IN ('accept', 'reduce')
        ORDER BY d.decision_time DESC
        LIMIT ?
        '''
        return [dict(row) for row in conn.execute(query, (limit,))]
    finally:
        conn.close()


def main() -> int:
    args = parse_args()
    profile = load_json(args.profile)
    db_path = Path(args.db_path or profile['paths']['signal_pipeline_db'])
    if not db_path.exists():
        raise FileNotFoundError(f'signal pipeline db not found: {db_path}')

    connector = build_connector(profile)
    idem = ExecutionIdempotencyStore(profile['paths']['execution_state_db'])
    execution_store = ExecutionStore(profile['paths']['execution_state_db'])
    default_quantity = float(profile.get('simulation', {}).get('default_quantity', 1.0))
    candidates = load_dispatch_candidates(db_path, args.limit)
    run_id = build_run_id('dispatch')
    summary = {'run_id': run_id, 'submitted': 0, 'deduplicated': 0, 'failed': 0, 'results': []}

    for item in candidates:
        trace = build_trace_context(stage='dispatch', run_id=run_id, seed=item['decision_id'])
        req = ExecutionDispatchRequest(
            decision_id=item['decision_id'],
            signal_id=item['signal_id'],
            strategy_name=item['strategy_name'],
            pair=item['pair'],
            side=item['side'],
            action=item['action'],
            order_type='market',
            stake_fraction=float(item.get('allocated_risk_fraction') or 0.0),
            entry_price=item.get('entry_price'),
            metadata={
                'allocated_notional': float(item.get('allocated_notional') or 0.0),
                'dispatch_kind': 'primary',
                'run_id': trace.run_id,
                'trace_id': trace.trace_id,
                'stage': trace.stage,
            },
        )
        payload = req.to_payload()
        request_hash = idem.build_request_hash(payload)
        existing = idem.get_existing_by_request_hash(item['decision_id'], request_hash)
        if existing:
            summary['deduplicated'] += 1
            summary['results'].append({
                'decision_id': item['decision_id'],
                'status': 'deduplicated',
                'remote_id': existing.get('remote_id'),
                'trace_id': existing.get('trace_id'),
            })
            continue
        try:
            result = connector.dispatch(req)
            order_id = f"exec:{item['decision_id']}"
            idem.record_dispatch(
                decision_id=item['decision_id'],
                signal_id=item['signal_id'],
                action=item['action'],
                pair=item['pair'],
                strategy_name=item['strategy_name'],
                request_payload=payload,
                dispatch_status=result.status,
                remote_id=result.remote_id,
                response_payload=result.response_payload,
                order_id=order_id,
                run_id=trace.run_id,
                trace_id=trace.trace_id,
            )
            execution_store.upsert_order(build_execution_order_record(
                order_id=order_id,
                decision_id=item['decision_id'],
                signal_id=item['signal_id'],
                strategy_name=item['strategy_name'],
                pair=item['pair'],
                side=item['side'],
                action=item['action'],
                order_type='market',
                requested_price=float(item['entry_price']) if item.get('entry_price') is not None else None,
                requested_stake_fraction=float(item.get('allocated_risk_fraction') or 0.0),
                requested_notional=float(item.get('allocated_notional') or 0.0),
                requested_quantity=default_quantity,
                dispatch_status=result.status,
                remote_id=result.remote_id,
                connector_mode=connector.mode,
                raw_response_json=json.dumps(result.response_payload, ensure_ascii=False) if result.response_payload is not None else None,
                run_id=trace.run_id,
                trace_id=trace.trace_id,
            ))
            summary['submitted'] += 1
            summary['results'].append({'decision_id': item['decision_id'], 'order_id': order_id, 'trace_id': trace.trace_id, **result.to_dict()})
        except Exception as exc:  # pragma: no cover - runtime path
            summary['failed'] += 1
            summary['results'].append({'decision_id': item['decision_id'], 'status': 'failed', 'trace_id': trace.trace_id, 'message': str(exc)})

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
