from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class DispatchLogRecord:
    idempotency_key: str
    decision_id: str
    signal_id: str
    action: str
    pair: str
    strategy_name: str
    request_hash: str
    dispatch_status: str
    remote_id: str | None
    dispatched_at: str
    response_json: str | None
    order_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    parent_trace_id: str | None = None


class ExecutionIdempotencyStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        existing = {row['name'] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()}
        if column not in existing:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}')

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS execution_dispatch_log (
                    idempotency_key TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    dispatch_status TEXT NOT NULL,
                    remote_id TEXT,
                    dispatched_at TEXT NOT NULL,
                    response_json TEXT
                )
                '''
            )
            self._ensure_column(conn, 'execution_dispatch_log', 'order_id', 'TEXT')
            self._ensure_column(conn, 'execution_dispatch_log', 'run_id', 'TEXT')
            self._ensure_column(conn, 'execution_dispatch_log', 'trace_id', 'TEXT')
            self._ensure_column(conn, 'execution_dispatch_log', 'parent_trace_id', 'TEXT')
            conn.execute('DROP INDEX IF EXISTS idx_execution_dispatch_decision')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_dispatch_decision_time ON execution_dispatch_log(decision_id, dispatched_at DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_dispatch_request_hash ON execution_dispatch_log(decision_id, request_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_dispatch_run_trace ON execution_dispatch_log(run_id, trace_id)')

    @staticmethod
    def build_request_hash(payload: dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(body.encode('utf-8')).hexdigest()

    @staticmethod
    def build_idempotency_key(decision_id: str, request_hash: str) -> str:
        return hashlib.sha256(f'{decision_id}:{request_hash}'.encode('utf-8')).hexdigest()

    def get_existing(self, decision_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM execution_dispatch_log WHERE decision_id = ? ORDER BY dispatched_at DESC LIMIT 1',
                (decision_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_existing_by_request_hash(self, decision_id: str, request_hash: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM execution_dispatch_log WHERE decision_id = ? AND request_hash = ? ORDER BY dispatched_at DESC LIMIT 1',
                (decision_id, request_hash),
            ).fetchone()
        return dict(row) if row else None

    def record(self, record: DispatchLogRecord) -> None:
        payload = asdict(record)
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT OR REPLACE INTO execution_dispatch_log (
                    idempotency_key, decision_id, signal_id, action, pair, strategy_name,
                    request_hash, dispatch_status, remote_id, dispatched_at, response_json,
                    order_id, run_id, trace_id, parent_trace_id
                ) VALUES (
                    :idempotency_key, :decision_id, :signal_id, :action, :pair, :strategy_name,
                    :request_hash, :dispatch_status, :remote_id, :dispatched_at, :response_json,
                    :order_id, :run_id, :trace_id, :parent_trace_id
                )
                ''',
                payload,
            )

    def record_dispatch(
        self,
        *,
        decision_id: str,
        signal_id: str = '',
        action: str = '',
        pair: str = '',
        strategy_name: str = '',
        request_payload: dict[str, Any] | None = None,
        request_hash: str | None = None,
        dispatch_status: str,
        remote_id: str | None = None,
        response_payload: dict[str, Any] | None = None,
        order_id: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
        parent_trace_id: str | None = None,
    ) -> dict[str, Any]:
        effective_request_hash = request_hash or self.build_request_hash(request_payload or {})
        record = DispatchLogRecord(
            idempotency_key=self.build_idempotency_key(decision_id, effective_request_hash),
            decision_id=decision_id,
            signal_id=signal_id,
            action=action,
            pair=pair,
            strategy_name=strategy_name,
            request_hash=effective_request_hash,
            dispatch_status=dispatch_status,
            remote_id=remote_id,
            dispatched_at=datetime.now(timezone.utc).isoformat(),
            response_json=json.dumps(response_payload, ensure_ascii=False) if response_payload is not None else None,
            order_id=order_id,
            run_id=run_id,
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
        )
        self.record(record)
        return asdict(record)
