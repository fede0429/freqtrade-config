from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_ORDER_TRANSITIONS: dict[str, set[str]] = {
    'submitted': {'submitted', 'accepted', 'partial', 'filled', 'failed', 'cancelled'},
    'accepted': {'accepted', 'partial', 'filled', 'failed', 'cancelled'},
    'partial': {'partial', 'filled', 'failed', 'cancelled'},
    'filled': {'filled'},
    'failed': {'failed', 'submitted'},
    'cancelled': {'cancelled', 'submitted'},
}


@dataclass
class ExecutionOrderRecord:
    order_id: str
    decision_id: str
    signal_id: str
    strategy_name: str
    pair: str
    side: str
    action: str
    order_type: str
    requested_price: float | None
    requested_stake_fraction: float
    requested_notional: float | None
    requested_quantity: float | None
    dispatch_status: str
    remote_id: str | None
    venue_order_id: str | None
    external_order_id: str | None
    order_status: str
    retry_count: int
    parent_order_id: str | None
    replace_reason: str | None
    average_fill_price: float | None
    executed_quantity: float | None
    fee_amount: float | None
    slippage_bps: float | None
    last_error: str | None
    error_category: str | None
    submitted_at: str
    accepted_at: str | None
    filled_at: str | None
    cancelled_at: str | None
    updated_at: str
    connector_mode: str
    raw_response_json: str | None
    run_id: str | None = None
    trace_id: str | None = None
    parent_trace_id: str | None = None


class ExecutionStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_orders (
                    order_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    side TEXT NOT NULL,
                    action TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    requested_price REAL,
                    requested_stake_fraction REAL NOT NULL,
                    requested_notional REAL,
                    dispatch_status TEXT NOT NULL,
                    remote_id TEXT,
                    venue_order_id TEXT,
                    order_status TEXT NOT NULL,
                    average_fill_price REAL,
                    executed_quantity REAL,
                    fee_amount REAL,
                    slippage_bps REAL,
                    last_error TEXT,
                    submitted_at TEXT NOT NULL,
                    accepted_at TEXT,
                    filled_at TEXT,
                    cancelled_at TEXT,
                    updated_at TEXT NOT NULL,
                    connector_mode TEXT NOT NULL,
                    raw_response_json TEXT
                )
                """
            )
            self._ensure_column(conn, 'execution_orders', 'requested_quantity', 'REAL')
            self._ensure_column(conn, 'execution_orders', 'retry_count', 'INTEGER NOT NULL DEFAULT 0')
            self._ensure_column(conn, 'execution_orders', 'parent_order_id', 'TEXT')
            self._ensure_column(conn, 'execution_orders', 'replace_reason', 'TEXT')
            self._ensure_column(conn, 'execution_orders', 'external_order_id', 'TEXT')
            self._ensure_column(conn, 'execution_orders', 'error_category', 'TEXT')
            self._ensure_column(conn, 'execution_orders', 'run_id', 'TEXT')
            self._ensure_column(conn, 'execution_orders', 'trace_id', 'TEXT')
            self._ensure_column(conn, 'execution_orders', 'parent_trace_id', 'TEXT')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_decision ON execution_orders(decision_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_status ON execution_orders(order_status, submitted_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_pair ON execution_orders(pair, submitted_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_parent ON execution_orders(parent_order_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_retry ON execution_orders(retry_count, updated_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_external ON execution_orders(external_order_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_venue_order ON execution_orders(venue_order_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_orders_run_trace ON execution_orders(run_id, trace_id)')

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_trade_reconciliation (
                    reconciliation_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    trade_id INTEGER,
                    trade_status TEXT,
                    match_type TEXT NOT NULL,
                    match_score REAL NOT NULL,
                    matched_by TEXT,
                    external_order_id TEXT,
                    venue_order_id TEXT,
                    trade_open_date TEXT,
                    trade_close_date TEXT,
                    trade_profit_abs REAL,
                    trade_profit_ratio REAL,
                    trade_fees REAL,
                    reconciled_at TEXT NOT NULL,
                    notes TEXT
                )
                """
            )
            self._ensure_column(conn, 'execution_trade_reconciliation', 'matched_by', 'TEXT')
            self._ensure_column(conn, 'execution_trade_reconciliation', 'external_order_id', 'TEXT')
            self._ensure_column(conn, 'execution_trade_reconciliation', 'venue_order_id', 'TEXT')
            self._ensure_column(conn, 'execution_trade_reconciliation', 'run_id', 'TEXT')
            self._ensure_column(conn, 'execution_trade_reconciliation', 'trace_id', 'TEXT')
            conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_trade_recon_order ON execution_trade_reconciliation(order_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_trade_recon_decision ON execution_trade_reconciliation(decision_id)')

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_order_events (
                    event_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT,
                    event_time TEXT NOT NULL,
                    run_id TEXT,
                    trace_id TEXT,
                    parent_trace_id TEXT,
                    payload_json TEXT
                )
                """
            )
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_order_events_order_time ON execution_order_events(order_id, event_time DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_order_events_run_trace ON execution_order_events(run_id, trace_id)')

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        existing = {row['name'] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()}
        if column not in existing:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}')

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def append_order_event(
        self,
        *,
        order_id: str,
        decision_id: str,
        signal_id: str,
        event_type: str,
        from_status: str | None,
        to_status: str | None,
        run_id: str | None,
        trace_id: str | None,
        parent_trace_id: str | None,
        payload: dict[str, Any] | None,
    ) -> None:
        event_time = self._utc_now()
        event_id = f"{order_id}:{event_type}:{event_time}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO execution_order_events (
                    event_id, order_id, decision_id, signal_id, event_type,
                    from_status, to_status, event_time, run_id, trace_id, parent_trace_id, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    order_id,
                    decision_id,
                    signal_id,
                    event_type,
                    from_status,
                    to_status,
                    event_time,
                    run_id,
                    trace_id,
                    parent_trace_id,
                    json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                ),
            )

    def upsert_order(self, record: ExecutionOrderRecord) -> None:
        payload = record.__dict__.copy()
        cols = ', '.join(payload.keys())
        placeholders = ', '.join('?' for _ in payload)
        update = ', '.join(f'{k}=excluded.{k}' for k in payload.keys() if k != 'order_id')
        existing = self.get_order(record.order_id)
        with self._connect() as conn:
            conn.execute(
                f"""
                INSERT INTO execution_orders ({cols})
                VALUES ({placeholders})
                ON CONFLICT(order_id) DO UPDATE SET {update}
                """,
                tuple(payload.values()),
            )
        if not existing:
            self.append_order_event(
                order_id=record.order_id,
                decision_id=record.decision_id,
                signal_id=record.signal_id,
                event_type='created',
                from_status=None,
                to_status=record.order_status,
                run_id=record.run_id,
                trace_id=record.trace_id,
                parent_trace_id=record.parent_trace_id,
                payload={'dispatch_status': record.dispatch_status, 'connector_mode': record.connector_mode},
            )

    def get_by_decision(self, decision_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM execution_orders WHERE decision_id = ? ORDER BY submitted_at DESC LIMIT 1', (decision_id,)).fetchone()
        return dict(row) if row else None

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM execution_orders WHERE order_id = ?', (order_id,)).fetchone()
        return dict(row) if row else None

    def list_order_events(self, order_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute('SELECT * FROM execution_order_events WHERE order_id = ? ORDER BY event_time ASC', (order_id,)).fetchall()
        return [dict(r) for r in rows]

    def list_open_orders(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM execution_orders
                WHERE order_status IN ('submitted', 'accepted', 'partial')
                ORDER BY submitted_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_retriable_orders(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM execution_orders
                WHERE order_status IN ('failed', 'cancelled', 'partial')
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_unreconciled_filled_orders(self, as_of_date: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = "eo.order_status = 'filled' AND r.order_id IS NULL"
        if as_of_date:
            where += ' AND eo.submitted_at LIKE ?'
            params.append(f'{as_of_date}%')
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT eo.*
                FROM execution_orders eo
                LEFT JOIN execution_trade_reconciliation r ON r.order_id = eo.order_id
                WHERE {where}
                ORDER BY eo.filled_at DESC, eo.submitted_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_orders_for_date(self, as_of_date: str) -> list[dict[str, Any]]:
        like = f'{as_of_date}%'
        with self._connect() as conn:
            rows = conn.execute('SELECT * FROM execution_orders WHERE submitted_at LIKE ? ORDER BY submitted_at DESC', (like,)).fetchall()
        return [dict(r) for r in rows]

    def mark_status(
        self,
        order_id: str,
        *,
        order_status: str,
        dispatch_status: str | None = None,
        venue_order_id: str | None = None,
        external_order_id: str | None = None,
        average_fill_price: float | None = None,
        executed_quantity: float | None = None,
        fee_amount: float | None = None,
        slippage_bps: float | None = None,
        last_error: str | None = None,
        error_category: str | None = None,
        raw_response_json: str | None = None,
        accepted_at: str | None = None,
        filled_at: str | None = None,
        cancelled_at: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
        parent_trace_id: str | None = None,
        force: bool = False,
    ) -> None:
        existing = self.get_order(order_id)
        if not existing:
            raise KeyError(f'order not found: {order_id}')
        current_status = str(existing.get('order_status') or 'submitted')
        allowed = ALLOWED_ORDER_TRANSITIONS.get(current_status, {current_status})
        if order_status not in allowed and not force:
            raise ValueError(f'invalid execution order transition: {current_status} -> {order_status}')
        updates = {'order_status': order_status, 'updated_at': self._utc_now()}
        optional = {
            'dispatch_status': dispatch_status,
            'venue_order_id': venue_order_id,
            'external_order_id': external_order_id,
            'average_fill_price': average_fill_price,
            'executed_quantity': executed_quantity,
            'fee_amount': fee_amount,
            'slippage_bps': slippage_bps,
            'last_error': last_error,
            'error_category': error_category,
            'raw_response_json': raw_response_json,
            'accepted_at': accepted_at,
            'filled_at': filled_at,
            'cancelled_at': cancelled_at,
            'run_id': run_id,
            'trace_id': trace_id,
            'parent_trace_id': parent_trace_id,
        }
        updates.update({k: v for k, v in optional.items() if v is not None})
        assignments = ', '.join(f'{k} = ?' for k in updates)
        with self._connect() as conn:
            conn.execute(f'UPDATE execution_orders SET {assignments} WHERE order_id = ?', (*updates.values(), order_id))
        self.append_order_event(
            order_id=order_id,
            decision_id=existing['decision_id'],
            signal_id=existing['signal_id'],
            event_type='status_change',
            from_status=current_status,
            to_status=order_status,
            run_id=run_id or existing.get('run_id'),
            trace_id=trace_id or existing.get('trace_id'),
            parent_trace_id=parent_trace_id or existing.get('parent_trace_id'),
            payload={'dispatch_status': dispatch_status, 'error_category': error_category, 'last_error': last_error},
        )

    def save_reconciliation(self, payload: dict[str, Any]) -> None:
        cols = ', '.join(payload.keys())
        placeholders = ', '.join('?' for _ in payload)
        update = ', '.join(f'{k}=excluded.{k}' for k in payload if k != 'reconciliation_id')
        with self._connect() as conn:
            conn.execute(
                f"""
                INSERT INTO execution_trade_reconciliation ({cols})
                VALUES ({placeholders})
                ON CONFLICT(reconciliation_id) DO UPDATE SET {update}
                """,
                tuple(payload.values()),
            )

    def list_state_anomalies(self) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT order_id, decision_id, order_status, filled_at, average_fill_price, executed_quantity, cancelled_at
                FROM execution_orders
                """
            ).fetchall()
        for row in rows:
            item = dict(row)
            status = item['order_status']
            if status == 'filled' and (item['filled_at'] is None or item['average_fill_price'] is None):
                anomalies.append({'order_id': item['order_id'], 'type': 'filled_missing_fill_fields'})
            if status == 'cancelled' and item['cancelled_at'] is None:
                anomalies.append({'order_id': item['order_id'], 'type': 'cancelled_missing_cancelled_at'})
            if status == 'partial' and item['executed_quantity'] in (None, 0, 0.0):
                anomalies.append({'order_id': item['order_id'], 'type': 'partial_missing_quantity'})
        return anomalies


def build_execution_order_record(
    *,
    order_id: str,
    decision_id: str,
    signal_id: str,
    strategy_name: str,
    pair: str,
    side: str,
    action: str,
    order_type: str,
    requested_price: float | None,
    requested_stake_fraction: float,
    requested_notional: float | None,
    requested_quantity: float | None,
    dispatch_status: str,
    remote_id: str | None,
    connector_mode: str,
    raw_response_json: str | None,
    venue_order_id: str | None = None,
    external_order_id: str | None = None,
    order_status: str | None = None,
    average_fill_price: float | None = None,
    executed_quantity: float | None = None,
    fee_amount: float | None = None,
    slippage_bps: float | None = None,
    last_error: str | None = None,
    error_category: str | None = None,
    retry_count: int = 0,
    parent_order_id: str | None = None,
    replace_reason: str | None = None,
    run_id: str | None = None,
    trace_id: str | None = None,
    parent_trace_id: str | None = None,
) -> ExecutionOrderRecord:
    now = datetime.now(timezone.utc).isoformat()
    effective_status = order_status or ('submitted' if dispatch_status in {'submitted', 'accepted', 'simulated'} else dispatch_status)
    return ExecutionOrderRecord(
        order_id=order_id,
        decision_id=decision_id,
        signal_id=signal_id,
        strategy_name=strategy_name,
        pair=pair,
        side=side,
        action=action,
        order_type=order_type,
        requested_price=requested_price,
        requested_stake_fraction=requested_stake_fraction,
        requested_notional=requested_notional,
        requested_quantity=requested_quantity,
        dispatch_status=dispatch_status,
        remote_id=remote_id,
        venue_order_id=venue_order_id,
        external_order_id=external_order_id,
        order_status=effective_status,
        retry_count=retry_count,
        parent_order_id=parent_order_id,
        replace_reason=replace_reason,
        average_fill_price=average_fill_price,
        executed_quantity=executed_quantity,
        fee_amount=fee_amount,
        slippage_bps=slippage_bps,
        last_error=last_error,
        error_category=error_category,
        submitted_at=now,
        accepted_at=now if effective_status in {'accepted', 'partial', 'filled'} else None,
        filled_at=now if effective_status == 'filled' else None,
        cancelled_at=now if effective_status == 'cancelled' else None,
        updated_at=now,
        connector_mode=connector_mode,
        raw_response_json=raw_response_json,
        run_id=run_id,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
    )
