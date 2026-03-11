from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from services.analytics.signal_pipeline_loader import load_signal_pipeline_summary


@dataclass
class ReportingInput:
    payload: dict[str, Any]
    source_meta: dict[str, Any]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _sqlite_meta(db_path: str | Path, trade_counts: dict[str, int] | None = None) -> dict[str, Any]:
    db = Path(db_path)
    exists = db.exists()
    return {
        'type': 'sqlite',
        'path': str(db),
        'db_path_basename': db.name,
        'db_exists': exists,
        'db_is_fixture': any(token in str(db).lower() for token in ('fixtures', 'sample', 'mock')),
        'db_last_modified': datetime.utcfromtimestamp(db.stat().st_mtime).isoformat() + 'Z' if exists else None,
        'closed_trade_count': trade_counts.get('closed', 0) if trade_counts else None,
        'open_trade_count': trade_counts.get('open', 0) if trade_counts else None,
    }


def load_reporting_input(profile: dict[str, Any]) -> ReportingInput:
    source = profile.get('input_source', {})
    source_type = source.get('type', 'json')
    if source_type == 'sqlite':
        db_path = source.get('db_path') or profile['paths'].get('pnl_input')
        as_of_date = source.get('as_of_date') or datetime.now().strftime('%Y-%m-%d')
        payload = load_freqtrade_sqlite(
            db_path=db_path,
            as_of_date=as_of_date,
            equity_start=float(source.get('equity_start', profile.get('summary_defaults', {}).get('capital_allocated_usd', 0.0))),
            unrealized_buffer=float(source.get('unrealized_buffer', 0.0)),
            risk_events=source.get('risk_events', []),
        )
        source_meta = _sqlite_meta(db_path, {
            'closed': len(payload.get('closed_trades', [])),
            'open': len(payload.get('open_positions', [])),
        })
        source_meta['as_of_date'] = as_of_date
        return ReportingInput(payload=payload, source_meta=source_meta)

    path = source.get('json_path') or profile['paths']['pnl_input']
    return ReportingInput(payload=load_json(path), source_meta={'type': 'json', 'path': path})


def load_optional_signal_pipeline(profile: dict[str, Any], as_of_date: str) -> dict[str, Any]:
    paths = profile.get('paths', {})
    db_path = paths.get('signal_pipeline_db')
    if not db_path:
        return {'available': False, 'execution_funnel': {}, 'missed_alpha': {}}
    return load_signal_pipeline_summary(db_path, as_of_date, paths.get('execution_state_db'))


def _trade_column_set(conn: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in conn.execute('PRAGMA table_info(trades)')}


def _best_column(columns: set[str], *candidates: str, default_sql: str = '0.0') -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return default_sql


def load_freqtrade_sqlite(
    db_path: str | Path,
    as_of_date: str,
    equity_start: float,
    unrealized_buffer: float = 0.0,
    risk_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    db = Path(db_path)
    if not db.exists():
        raise FileNotFoundError(f'SQLite file not found: {db}')

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        trade_columns = _trade_column_set(conn)
        profit_abs_col = _best_column(trade_columns, 'close_profit_abs', 'profit_abs', 'realized_profit')
        profit_ratio_col = _best_column(trade_columns, 'close_profit', 'profit_ratio')
        strategy_col = _best_column(trade_columns, 'strategy', default_sql="''")
        trade_duration_col = _best_column(trade_columns, 'trade_duration', default_sql='0')
        stake_amount_col = _best_column(trade_columns, 'stake_amount', 'open_trade_value')
        is_short_col = _best_column(trade_columns, 'is_short', default_sql='0')

        start_ts = f'{as_of_date}T00:00:00+00:00'
        end_ts = f'{as_of_date}T23:59:59+00:00'
        closed = [
            dict(row)
            for row in conn.execute(
                f'''
                SELECT
                    pair,
                    {strategy_col} AS strategy,
                    COALESCE({profit_abs_col}, 0.0) AS pnl_usd,
                    COALESCE({profit_ratio_col}, 0.0) AS profit_ratio,
                    close_date,
                    COALESCE({trade_duration_col}, 0) AS trade_duration,
                    COALESCE(fee_open, 0.0) + COALESCE(fee_close, 0.0) AS fees
                FROM trades
                WHERE is_open = 0
                  AND close_date >= ?
                  AND close_date <= ?
                ORDER BY close_date DESC
                ''',
                (start_ts, end_ts),
            )
        ]

        open_positions = [
            dict(row)
            for row in conn.execute(
                f'''
                SELECT
                    pair,
                    {strategy_col} AS strategy,
                    CASE WHEN COALESCE({is_short_col}, 0) = 1 THEN 'short' ELSE 'long' END AS side,
                    COALESCE({stake_amount_col}, 0.0) AS exposure_usd,
                    0.0 AS pnl_usd,
                    open_date
                FROM trades
                WHERE is_open = 1
                ORDER BY open_date DESC
                '''
            )
        ]
    finally:
        conn.close()

    realized = round(sum(float(item.get('pnl_usd', 0.0) or 0.0) for item in closed), 2)
    fees = round(sum(float(item.get('fees', 0.0) or 0.0) for item in closed), 2)
    unrealized = round(sum(float(item.get('pnl_usd', 0.0) or 0.0) for item in open_positions) + unrealized_buffer, 2)
    equity_end = round(equity_start + realized + unrealized - fees, 2)
    max_drawdown_ratio = _estimate_drawdown_ratio(equity_start, closed)
    win_rate = _win_rate(closed)
    profit_factor = _profit_factor(closed)

    return {
        'date': as_of_date,
        'equity_start': equity_start,
        'equity_end': equity_end,
        'realized_pnl': realized,
        'unrealized_pnl': unrealized,
        'fees': fees,
        'max_drawdown_ratio': max_drawdown_ratio,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'open_positions': open_positions,
        'closed_trades': closed,
        'risk_events': risk_events or [],
    }


def _win_rate(trades: list[dict[str, Any]]) -> float:
    if not trades:
        return 0.0
    winners = sum(1 for item in trades if float(item.get('pnl_usd', 0.0) or 0.0) > 0)
    return round(winners / len(trades), 4)


def _profit_factor(trades: list[dict[str, Any]]) -> float:
    gains = sum(float(item.get('pnl_usd', 0.0) or 0.0) for item in trades if float(item.get('pnl_usd', 0.0) or 0.0) > 0)
    losses = abs(sum(float(item.get('pnl_usd', 0.0) or 0.0) for item in trades if float(item.get('pnl_usd', 0.0) or 0.0) < 0))
    if losses == 0:
        return round(gains, 4) if gains > 0 else 0.0
    return round(gains / losses, 4)


def _estimate_drawdown_ratio(equity_start: float, trades: list[dict[str, Any]]) -> float:
    if equity_start <= 0 or not trades:
        return 0.0
    ordered = sorted(trades, key=lambda item: item.get('close_date', ''))
    curve = equity_start
    peak = equity_start
    max_dd = 0.0
    for item in ordered:
        curve += float(item.get('pnl_usd', 0.0) or 0.0) - float(item.get('fees', 0.0) or 0.0)
        peak = max(peak, curve)
        dd = (peak - curve) / peak if peak else 0.0
        max_dd = max(max_dd, dd)
    return round(max_dd, 4)
