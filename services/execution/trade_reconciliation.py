from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.execution.execution_store import ExecutionStore

STRONG_KEYS = ('external_order_id', 'venue_order_id', 'remote_id')
TRADE_KEY_CANDIDATES = ('order_id', 'ft_order_id', 'exchange_order_id', 'client_order_id')


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def reconcile_execution_trades(*, execution_db_path: str | Path, trades_db_path: str | Path, as_of_date: str | None = None, tolerance_minutes: int = 24 * 60, limit: int = 100, run_id: str | None = None) -> dict[str, Any]:
    execution_store = ExecutionStore(execution_db_path)
    orders = execution_store.list_unreconciled_filled_orders(as_of_date=as_of_date, limit=limit)
    trades_db = Path(trades_db_path)
    if not trades_db.exists():
        raise FileNotFoundError(f'trades db not found: {trades_db}')
    conn = sqlite3.connect(str(trades_db))
    conn.row_factory = sqlite3.Row
    trade_cols = _table_columns(conn, 'trades')
    try:
        summary = {'run_id': run_id, 'processed': 0, 'matched': 0, 'strong_matched': 0, 'heuristic_matched': 0, 'unmatched': 0, 'results': []}
        for order in orders:
            match = _find_trade_match(conn, trade_cols, order, tolerance_minutes=tolerance_minutes)
            summary['processed'] += 1
            if not match:
                summary['unmatched'] += 1
                summary['results'].append({'order_id': order['order_id'], 'status': 'unmatched'})
                continue
            payload = {
                'reconciliation_id': hashlib.sha256(order['order_id'].encode('utf-8')).hexdigest(),
                'order_id': order['order_id'],
                'decision_id': order['decision_id'],
                'signal_id': order['signal_id'],
                'trade_id': int(match['id']),
                'trade_status': 'open' if int(match.get('is_open') or 0) == 1 else 'closed',
                'match_type': match['_match_type'],
                'match_score': round(float(match['_match_score']), 4),
                'matched_by': match.get('_matched_by'),
                'external_order_id': order.get('external_order_id'),
                'venue_order_id': order.get('venue_order_id'),
                'trade_open_date': match.get('open_date'),
                'trade_close_date': match.get('close_date'),
                'trade_profit_abs': float(match.get('profit_abs') or 0.0),
                'trade_profit_ratio': float(match.get('profit_ratio') or 0.0),
                'trade_fees': float(match.get('fee_open') or 0.0) + float(match.get('fee_close') or 0.0),
                'reconciled_at': datetime.now(timezone.utc).isoformat(),
                'notes': json.dumps({'pair': order['pair'], 'strategy_name': order['strategy_name']}, ensure_ascii=False),
                'run_id': run_id,
                'trace_id': order.get('trace_id'),
            }
            execution_store.save_reconciliation(payload)
            summary['matched'] += 1
            if match['_match_type'] == 'strong_key':
                summary['strong_matched'] += 1
            else:
                summary['heuristic_matched'] += 1
            summary['results'].append({'order_id': order['order_id'], 'status': 'matched', 'trade_id': payload['trade_id'], 'match_type': payload['match_type'], 'matched_by': payload['matched_by'], 'match_score': payload['match_score']})
        return summary
    finally:
        conn.close()


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
        return {str(r[1]) for r in rows}
    except sqlite3.OperationalError:
        return set()


def _find_trade_match(conn: sqlite3.Connection, trade_cols: set[str], order: dict[str, Any], tolerance_minutes: int) -> dict[str, Any] | None:
    strong = _find_strong_key_match(conn, trade_cols, order)
    if strong:
        strong['_match_type'] = 'strong_key'
        strong['_match_score'] = 1.0
        return strong
    return _find_heuristic_match(conn, order, tolerance_minutes)


def _find_strong_key_match(conn: sqlite3.Connection, trade_cols: set[str], order: dict[str, Any]) -> dict[str, Any] | None:
    for order_key in STRONG_KEYS:
        val = order.get(order_key)
        if not val:
            continue
        for trade_col in TRADE_KEY_CANDIDATES:
            if trade_col not in trade_cols:
                continue
            row = conn.execute(f'SELECT * FROM trades WHERE {trade_col} = ? ORDER BY open_date DESC LIMIT 1', (str(val),)).fetchone()
            if row:
                d = dict(row)
                d['_matched_by'] = f'{order_key}->{trade_col}'
                return d
    return None


def _find_heuristic_match(conn: sqlite3.Connection, order: dict[str, Any], tolerance_minutes: int) -> dict[str, Any] | None:
    pair = order['pair']
    strategy_name = order['strategy_name']
    requested_price = _to_float(order.get('requested_price'))
    fill_price = _to_float(order.get('average_fill_price')) or requested_price
    pivot = _parse_dt(order.get('filled_at')) or _parse_dt(order.get('submitted_at'))
    if not pivot:
        return None
    rows = [dict(r) for r in conn.execute("SELECT * FROM trades WHERE pair = ? AND strategy = ? ORDER BY open_date DESC LIMIT 50", (pair, strategy_name)).fetchall()]
    if not rows:
        rows = [dict(r) for r in conn.execute("SELECT * FROM trades WHERE pair = ? ORDER BY open_date DESC LIMIT 50", (pair,)).fetchall()]
    best: tuple[float, dict[str, Any]] | None = None
    for row in rows:
        opened = _parse_dt(row.get('open_date'))
        if not opened:
            continue
        minutes_apart = abs((opened - pivot).total_seconds()) / 60.0
        if minutes_apart > tolerance_minutes:
            continue
        score = 1.0
        if row.get('strategy') == strategy_name:
            score += 0.7
        score += max(0.0, 1.0 - minutes_apart / tolerance_minutes)
        open_rate = _to_float(row.get('open_rate'))
        if fill_price and open_rate and fill_price > 0:
            price_diff = abs(open_rate - fill_price) / fill_price
            score += max(0.0, 1.0 - min(price_diff, 1.0))
        if best is None or score > best[0]:
            row['_match_type'] = 'heuristic'
            row['_match_score'] = score
            row['_matched_by'] = 'pair+strategy+time+price'
            best = (score, row)
    return best[1] if best else None


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
