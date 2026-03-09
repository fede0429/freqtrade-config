from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


PIPELINE_TABLES = {
    'strategy_signals': ('signal_id', 'event_time'),
    'decision_events': ('decision_id', 'decision_time'),
    'shadow_positions': ('shadow_id', 'opened_at'),
}


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    try:
        cols = conn.execute(f'PRAGMA table_info({table})').fetchall()
    except sqlite3.OperationalError:
        return False
    return any(str(r[1]) == column for r in cols)


def _safe_exec(conn: sqlite3.Connection, sql: str) -> None:
    try:
        conn.execute(sql)
    except sqlite3.OperationalError:
        pass


def ensure_trace_columns(db_path: str | Path) -> dict[str, Any]:
    db_path = Path(db_path)
    added: dict[str, list[str]] = {}
    with _connect(db_path) as conn:
        for table, (pk, _) in PIPELINE_TABLES.items():
            try:
                conn.execute(f'SELECT 1 FROM {table} LIMIT 1')
            except sqlite3.OperationalError:
                continue
            table_added: list[str] = []
            for column in ('run_id', 'trace_id', 'parent_trace_id', 'created_at', 'updated_at'):
                if not _has_column(conn, table, column):
                    conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} TEXT')
                    table_added.append(column)
            if table_added:
                added[table] = table_added
            _safe_exec(conn, f'CREATE UNIQUE INDEX IF NOT EXISTS ux_{table}_{pk} ON {table}({pk})')
            _safe_exec(conn, f'CREATE INDEX IF NOT EXISTS ix_{table}_trace_id ON {table}(trace_id)')
            _safe_exec(conn, f'CREATE INDEX IF NOT EXISTS ix_{table}_run_id ON {table}(run_id)')
        conn.commit()
    return {'db_path': str(db_path), 'added_columns': added}


def backfill_trace_columns(db_path: str | Path) -> dict[str, Any]:
    db_path = Path(db_path)
    result: dict[str, Any] = {'db_path': str(db_path), 'tables': {}}
    with _connect(db_path) as conn:
        for table, (pk, ts_col) in PIPELINE_TABLES.items():
            try:
                conn.execute(f'SELECT 1 FROM {table} LIMIT 1')
            except sqlite3.OperationalError:
                continue
            if not _has_column(conn, table, 'trace_id'):
                continue
            rows = conn.execute(
                f'''SELECT {pk} AS row_id, {ts_col} AS ts, run_id, trace_id, parent_trace_id, created_at, updated_at FROM {table}'''
            ).fetchall()
            updated = 0
            for row in rows:
                row_id = row['row_id']
                ts = row['ts'] or ''
                run_id = row['run_id'] or f'backfill:{table}:{str(ts)[:10] or "unknown"}'
                trace_id = row['trace_id'] or f'{table}:{row_id}'
                parent_trace_id = row['parent_trace_id']
                created_at = row['created_at'] or ts
                updated_at = row['updated_at'] or ts
                if any(row[c] is None for c in ('run_id', 'trace_id', 'created_at', 'updated_at')):
                    conn.execute(
                        f'''UPDATE {table}
                            SET run_id = COALESCE(run_id, ?),
                                trace_id = COALESCE(trace_id, ?),
                                parent_trace_id = COALESCE(parent_trace_id, ?),
                                created_at = COALESCE(created_at, ?),
                                updated_at = COALESCE(updated_at, ?)
                            WHERE {pk} = ?''',
                        (run_id, trace_id, parent_trace_id, created_at, updated_at, row_id),
                    )
                    updated += 1
            result['tables'][table] = {'rows': len(rows), 'updated': updated}
        conn.commit()
    return result


def trace_coverage(db_path: str | Path, as_of_date: str | None = None) -> dict[str, Any]:
    db_path = Path(db_path)
    output: dict[str, Any] = {'db_path': str(db_path), 'tables': {}, 'overall_ratio': 0.0}
    ratios = []
    with _connect(db_path) as conn:
        for table, (_, ts_col) in PIPELINE_TABLES.items():
            try:
                conn.execute(f'SELECT 1 FROM {table} LIMIT 1')
            except sqlite3.OperationalError:
                continue
            if not _has_column(conn, table, 'trace_id'):
                output['tables'][table] = {'rows': 0, 'traced_rows': 0, 'ratio': 0.0}
                continue
            params: tuple[Any, ...] = ()
            where = ''
            if as_of_date:
                where = f' WHERE {ts_col} LIKE ?'
                params = (f'{as_of_date}%',)
            row = conn.execute(
                f'''SELECT COUNT(*) AS rows,
                           SUM(CASE WHEN run_id IS NOT NULL AND trace_id IS NOT NULL THEN 1 ELSE 0 END) AS traced_rows
                    FROM {table}{where}''',
                params,
            ).fetchone()
            total = int(row['rows'] or 0)
            traced = int(row['traced_rows'] or 0)
            ratio = round((traced / total), 4) if total else 0.0
            output['tables'][table] = {'rows': total, 'traced_rows': traced, 'ratio': ratio}
            if total:
                ratios.append(ratio)
    output['overall_ratio'] = round(sum(ratios) / len(ratios), 4) if ratios else 0.0
    return output
