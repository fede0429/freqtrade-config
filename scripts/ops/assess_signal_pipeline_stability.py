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
    p = argparse.ArgumentParser(description='Assess signal pipeline stability and consistency.')
    p.add_argument('--signal-pipeline-db', required=True)
    p.add_argument('--execution-db', required=True)
    p.add_argument('--as-of-date', default=None)
    p.add_argument('--output-json', default=None)
    p.add_argument('--output-md', default=None)
    return p.parse_args()


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] or 0) if row else 0
    except sqlite3.OperationalError:
        return 0


def render_md(result: dict[str, Any]) -> str:
    checks = result['checks']
    lines = [
        '# Signal Pipeline Stability',
        '',
        f"- Score: {result['score']}",
        f"- Status: {result['status']}",
        '',
        '## Checks',
        f"- duplicate_dispatches: {checks['duplicate_dispatches']}",
        f"- orphan_execution_orders: {checks['orphan_execution_orders']}",
        f"- filled_unreconciled_orders: {checks['filled_unreconciled_orders']}",
        f"- order_state_anomalies: {checks['order_state_anomalies']}",
        f"- trace_coverage_ratio: {checks['trace_coverage_ratio']:.4f}",
        '',
        '## Warnings',
    ]
    if result['warnings']:
        for item in result['warnings']:
            lines.append(f'- {item}')
    else:
        lines.append('- none')
    return '\n'.join(lines) + '\n'


def main() -> int:
    args = parse_args()
    pipe_db = Path(args.signal_pipeline_db)
    exec_db = Path(args.execution_db)
    if not pipe_db.exists() or not exec_db.exists():
        raise FileNotFoundError('db not found')
    pipe = sqlite3.connect(str(pipe_db))
    pipe.row_factory = sqlite3.Row
    exe = sqlite3.connect(str(exec_db))
    exe.row_factory = sqlite3.Row
    try:
        decision_ids = [row[0] for row in pipe.execute('SELECT decision_id FROM decision_events').fetchall()]
        ph = ','.join('?' for _ in decision_ids) if decision_ids else ''
        duplicate_dispatches = _scalar(exe, 'SELECT COUNT(*) FROM (SELECT decision_id, request_hash FROM execution_dispatch_log GROUP BY decision_id, request_hash HAVING COUNT(*) > 1)')
        if decision_ids:
            orphan_orders = _scalar(exe, f'SELECT COUNT(*) FROM execution_orders WHERE decision_id NOT IN ({ph})', tuple(decision_ids))
        else:
            orphan_orders = _scalar(exe, 'SELECT COUNT(*) FROM execution_orders')
        if args.as_of_date:
            filled_unreconciled = _scalar(exe, "SELECT COUNT(*) FROM execution_orders eo LEFT JOIN execution_trade_reconciliation r ON r.order_id = eo.order_id WHERE eo.order_status='filled' AND r.order_id IS NULL AND eo.submitted_at LIKE ?", (f'{args.as_of_date}%',))
            trace_row = exe.execute("SELECT COUNT(*) AS orders, SUM(CASE WHEN run_id IS NOT NULL AND trace_id IS NOT NULL THEN 1 ELSE 0 END) AS traced FROM execution_orders WHERE submitted_at LIKE ?", (f'{args.as_of_date}%',)).fetchone()
        else:
            filled_unreconciled = _scalar(exe, "SELECT COUNT(*) FROM execution_orders eo LEFT JOIN execution_trade_reconciliation r ON r.order_id = eo.order_id WHERE eo.order_status='filled' AND r.order_id IS NULL")
            trace_row = exe.execute("SELECT COUNT(*) AS orders, SUM(CASE WHEN run_id IS NOT NULL AND trace_id IS NOT NULL THEN 1 ELSE 0 END) AS traced FROM execution_orders").fetchone()
        state_anomalies = len(ExecutionStore(exec_db).list_state_anomalies())
        orders = int(trace_row['orders'] or 0)
        traced = int(trace_row['traced'] or 0)
        ratio = round((traced / orders), 4) if orders else 0.0
        score = 100 - duplicate_dispatches * 10 - orphan_orders * 8 - filled_unreconciled * 10 - state_anomalies * 6 - int(max(0, 1 - ratio) * 20)
        status = 'healthy' if score >= 90 else 'watch' if score >= 75 else 'degraded'
        warnings = []
        if duplicate_dispatches:
            warnings.append(f'duplicate dispatch rows: {duplicate_dispatches}')
        if orphan_orders:
            warnings.append(f'orphan execution orders: {orphan_orders}')
        if filled_unreconciled:
            warnings.append(f'filled but unreconciled orders: {filled_unreconciled}')
        if state_anomalies:
            warnings.append(f'execution state anomalies: {state_anomalies}')
        if ratio < 1.0:
            warnings.append(f'trace coverage below 100%: {ratio:.2%}')
        result = {
            'score': score,
            'status': status,
            'checks': {
                'duplicate_dispatches': duplicate_dispatches,
                'orphan_execution_orders': orphan_orders,
                'filled_unreconciled_orders': filled_unreconciled,
                'order_state_anomalies': state_anomalies,
                'trace_coverage_ratio': ratio,
            },
            'warnings': warnings,
        }
        if args.output_json:
            Path(args.output_json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        if args.output_md:
            Path(args.output_md).write_text(render_md(result), encoding='utf-8')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        pipe.close()
        exe.close()


if __name__ == '__main__':
    raise SystemExit(main())
