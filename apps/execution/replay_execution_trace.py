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

from services.execution.execution_store import ExecutionStore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Replay one decision/order/signal execution trace.')
    p.add_argument('--profile', required=True)
    p.add_argument('--decision-id', default=None)
    p.add_argument('--order-id', default=None)
    p.add_argument('--signal-id', default=None)
    return p.parse_args()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def main() -> int:
    args = parse_args()
    profile = load_json(args.profile)
    pipeline_db = Path(profile['paths']['signal_pipeline_db'])
    execution_db = Path(profile['paths']['execution_state_db'])
    if not pipeline_db.exists() or not execution_db.exists():
        raise FileNotFoundError('required db not found')
    if not any([args.decision_id, args.order_id, args.signal_id]):
        raise SystemExit('provide --decision-id or --order-id or --signal-id')

    exec_store = ExecutionStore(execution_db)
    exec_conn = sqlite3.connect(str(execution_db))
    exec_conn.row_factory = sqlite3.Row
    pipe_conn = sqlite3.connect(str(pipeline_db))
    pipe_conn.row_factory = sqlite3.Row
    try:
        order = None
        decision = None
        signal = None
        if args.order_id:
            order = exec_store.get_order(args.order_id)
            if order:
                decision = _one(pipe_conn, 'SELECT * FROM decision_events WHERE decision_id = ?', (order['decision_id'],))
                signal = _one(pipe_conn, 'SELECT * FROM strategy_signals WHERE signal_id = ?', (order['signal_id'],))
        elif args.decision_id:
            decision = _one(pipe_conn, 'SELECT * FROM decision_events WHERE decision_id = ?', (args.decision_id,))
            if decision:
                signal = _one(pipe_conn, 'SELECT * FROM strategy_signals WHERE signal_id = ?', (decision['signal_id'],))
                order = _one(exec_conn, 'SELECT * FROM execution_orders WHERE decision_id = ? ORDER BY submitted_at DESC LIMIT 1', (decision['decision_id'],))
        else:
            signal = _one(pipe_conn, 'SELECT * FROM strategy_signals WHERE signal_id = ?', (args.signal_id,))
            if signal:
                decision = _one(pipe_conn, 'SELECT * FROM decision_events WHERE signal_id = ? ORDER BY decision_time DESC LIMIT 1', (signal['signal_id'],))
                if decision:
                    order = _one(exec_conn, 'SELECT * FROM execution_orders WHERE decision_id = ? ORDER BY submitted_at DESC LIMIT 1', (decision['decision_id'],))
        shadow = None
        if decision:
            shadow = _one(pipe_conn, 'SELECT * FROM shadow_positions WHERE decision_id = ? ORDER BY opened_at DESC LIMIT 1', (decision['decision_id'],))
        elif signal:
            shadow = _one(pipe_conn, 'SELECT * FROM shadow_positions WHERE signal_id = ? ORDER BY opened_at DESC LIMIT 1', (signal['signal_id'],))
        replay = {
            'signal': signal,
            'decision': decision,
            'shadow': shadow,
            'order': order,
            'dispatch_logs': [],
            'order_events': [],
            'reconciliation': None,
            'trace_summary': {
                'signal_trace_id': signal.get('trace_id') if signal else None,
                'decision_trace_id': decision.get('trace_id') if decision else None,
                'shadow_trace_id': shadow.get('trace_id') if shadow else None,
                'order_trace_id': order.get('trace_id') if order else None,
            },
        }
        if decision:
            replay['dispatch_logs'] = [dict(r) for r in exec_conn.execute('SELECT * FROM execution_dispatch_log WHERE decision_id = ? ORDER BY dispatched_at ASC', (decision['decision_id'],)).fetchall()]
        if order:
            replay['order_events'] = exec_store.list_order_events(order['order_id'])
            replay['reconciliation'] = _one(exec_conn, 'SELECT * FROM execution_trade_reconciliation WHERE order_id = ?', (order['order_id'],))
        print(json.dumps(replay, indent=2, ensure_ascii=False))
        return 0
    finally:
        exec_conn.close()
        pipe_conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
