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
from services.execution.trade_reconciliation import reconcile_execution_trades
from services.execution.trace import build_run_id, build_trace_context


PIPELINE_TABLES = (
    ('strategy_signals', 'signal_id', 'event_time'),
    ('decision_events', 'decision_id', 'decision_time'),
    ('shadow_positions', 'shadow_id', 'opened_at'),
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Auto-repair common signal-pipeline integrity issues.')
    p.add_argument('--signal-pipeline-db', required=True)
    p.add_argument('--execution-db', required=True)
    p.add_argument('--trades-db', default=None)
    p.add_argument('--profile', default=None, help='Execution profile JSON. Used to resolve trades_db when omitted.')
    p.add_argument('--as-of-date', default=None)
    p.add_argument('--fix', action='append', choices=['trace', 'unreconciled'], default=[])
    p.add_argument('--apply', action='store_true')
    return p.parse_args()


def _load_profile(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return bool(row)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(r[1]) for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}
    except sqlite3.OperationalError:
        return set()


def _ensure_cols(conn: sqlite3.Connection, table: str) -> None:
    cols = _columns(conn, table)
    for name in ('run_id', 'trace_id', 'parent_trace_id', 'created_at', 'updated_at'):
        if name not in cols:
            ddl = 'TEXT'
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')


def repair_trace(signal_pipeline_db: Path, execution_db: Path, apply: bool, as_of_date: str | None) -> dict[str, Any]:
    summary: dict[str, Any] = {'tables': {}, 'execution_orders': {'updated': 0}}
    run_id = build_run_id('repair-trace')
    pipe = sqlite3.connect(str(signal_pipeline_db))
    pipe.row_factory = sqlite3.Row
    try:
        for table, id_col, ts_col in PIPELINE_TABLES:
            if not _has_table(pipe, table):
                continue
            _ensure_cols(pipe, table)
            params: tuple[Any, ...] = ()
            sql = f"SELECT {id_col} AS entity_id, {ts_col} AS ts, run_id, trace_id FROM {table}"
            if as_of_date:
                sql += f" WHERE {ts_col} LIKE ?"
                params = (f'{as_of_date}%',)
            rows = pipe.execute(sql, params).fetchall()
            updated = 0
            for row in rows:
                need_run = not row['run_id']
                need_trace = not row['trace_id']
                if not need_run and not need_trace:
                    continue
                updated += 1
                if apply:
                    ts = row['ts'] or ''
                    backfill_run = row['run_id'] or f'{run_id}:{table}'
                    backfill_trace = row['trace_id'] or build_trace_context(stage=table, run_id=backfill_run, seed=f"{row['entity_id']}:{ts}").trace_id
                    pipe.execute(
                        f"UPDATE {table} SET run_id = COALESCE(run_id, ?), trace_id = COALESCE(trace_id, ?), updated_at = COALESCE(updated_at, ?), created_at = COALESCE(created_at, ?) WHERE {id_col} = ?",
                        (backfill_run, backfill_trace, ts or None, ts or None, row['entity_id']),
                    )
            summary['tables'][table] = {'updated': updated, 'checked': len(rows)}
        if apply:
            pipe.commit()
    finally:
        pipe.close()

    store = ExecutionStore(execution_db)
    conn = sqlite3.connect(str(execution_db))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT order_id, submitted_at, run_id, trace_id FROM execution_orders" + (" WHERE submitted_at LIKE ?" if as_of_date else ''), ((f'{as_of_date}%',) if as_of_date else ())).fetchall()
        updated = 0
        for row in rows:
            if row['run_id'] and row['trace_id']:
                continue
            updated += 1
            if apply:
                order = store.get_order(str(row['order_id']))
                if not order:
                    continue
                with sqlite3.connect(str(execution_db)) as wconn:
                    wconn.execute(
                        'UPDATE execution_orders SET run_id = COALESCE(run_id, ?), trace_id = COALESCE(trace_id, ?), parent_trace_id = COALESCE(parent_trace_id, ?) WHERE order_id = ?',
                        (f'{run_id}:execution', build_trace_context(stage='execution', run_id=f'{run_id}:execution', seed=f"{order['decision_id']}:{order.get('submitted_at', '')}:{order['order_id']}").trace_id, order.get('trace_id') or build_trace_context(stage='execution', run_id=f'{run_id}:execution', seed=f"{order['decision_id']}:{order.get('submitted_at', '')}:{order['order_id']}").trace_id, order['order_id']),
                    )
        summary['execution_orders'] = {'updated': updated, 'checked': len(rows)}
    finally:
        conn.close()
    return summary


def repair_unreconciled(execution_db: Path, trades_db: Path | None, apply: bool, as_of_date: str | None) -> dict[str, Any]:
    store = ExecutionStore(execution_db)
    pending = store.list_unreconciled_filled_orders(as_of_date=as_of_date, limit=500)
    result: dict[str, Any] = {'pending_filled_unreconciled': len(pending), 'matched': 0, 'processed': 0}
    if not apply or not trades_db:
        return result
    summary = reconcile_execution_trades(
        execution_db_path=execution_db,
        trades_db_path=trades_db,
        as_of_date=as_of_date,
        tolerance_minutes=24 * 60,
        limit=500,
        run_id=build_run_id('repair-reconcile'),
    )
    result.update({k: summary.get(k) for k in ('processed', 'matched', 'strong_matched', 'heuristic_matched', 'unmatched')})
    return result


def main() -> int:
    args = parse_args()
    profile = _load_profile(args.profile)
    trades_db = Path(args.trades_db or profile.get('paths', {}).get('trades_db', '')) if (args.trades_db or profile) else None
    repairs: dict[str, Any] = {'apply': args.apply, 'fixes': args.fix, 'results': {}}
    if 'trace' in args.fix:
        repairs['results']['trace'] = repair_trace(Path(args.signal_pipeline_db), Path(args.execution_db), args.apply, args.as_of_date)
    if 'unreconciled' in args.fix:
        repairs['results']['unreconciled'] = repair_unreconciled(Path(args.execution_db), trades_db, args.apply, args.as_of_date)
    print(json.dumps(repairs, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
