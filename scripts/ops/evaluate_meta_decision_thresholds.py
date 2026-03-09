#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate recent meta-decision and execution outcomes.')
    p.add_argument('--signal-pipeline-db', required=True)
    p.add_argument('--execution-db', required=True)
    p.add_argument('--as-of-date', default=None)
    return p.parse_args()


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row[1] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()}
    except sqlite3.OperationalError:
        return set()


def main() -> int:
    args = parse_args()
    pipe = sqlite3.connect(args.signal_pipeline_db)
    pipe.row_factory = sqlite3.Row
    exe = sqlite3.connect(args.execution_db)
    exe.row_factory = sqlite3.Row
    try:
        day_like = f"{args.as_of_date}%" if args.as_of_date else '%'
        dec_cols = _cols(pipe, 'decision_events')
        score_expr = 'AVG(COALESCE(decision_score, 0.0))' if 'decision_score' in dec_cols else 'NULL'
        decisions = [dict(r) for r in pipe.execute(f'SELECT action, COUNT(*) AS cnt, {score_expr} AS avg_score FROM decision_events WHERE decision_time LIKE ? GROUP BY action ORDER BY cnt DESC', (day_like,)).fetchall()]
        strategies = [dict(r) for r in pipe.execute(f'''
            SELECT s.strategy_name, d.action, COUNT(*) AS cnt, {score_expr.replace('decision_score', 'd.decision_score')} AS avg_score
            FROM decision_events d JOIN strategy_signals s ON s.signal_id = d.signal_id
            WHERE d.decision_time LIKE ?
            GROUP BY s.strategy_name, d.action
            ORDER BY s.strategy_name, cnt DESC
        ''', (day_like,)).fetchall()]
        fills = [dict(r) for r in exe.execute('SELECT action, order_status, COUNT(*) AS cnt, AVG(COALESCE(slippage_bps,0.0)) AS avg_slippage_bps FROM execution_orders WHERE submitted_at LIKE ? GROUP BY action, order_status ORDER BY action, cnt DESC', (day_like,)).fetchall()]
        result = {
            'date_filter': args.as_of_date,
            'decision_distribution': decisions,
            'strategy_action_distribution': strategies,
            'execution_outcomes': fills,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        pipe.close()
        exe.close()


if __name__ == '__main__':
    raise SystemExit(main())
