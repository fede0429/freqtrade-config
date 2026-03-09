from __future__ import annotations

import sqlite3
from pathlib import Path

from services.execution.pipeline_trace import trace_coverage
from typing import Any


def load_signal_pipeline_summary(db_path: str | Path, as_of_date: str, execution_db_path: str | Path | None = None) -> dict[str, Any]:
    db = Path(db_path)
    execution_db = Path(execution_db_path) if execution_db_path else db
    if not db.exists():
        return {
            'available': False,
            'db_path': str(db),
            'execution_funnel': {},
            'missed_alpha': {},
            'decision_to_fill': {},
            'outcome_comparison': {},
            'replace_cost_analysis': {},
            'integrity_checks': {},
            'traceability': {},
            'alert_summary': {},
        }

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        day_like = f'{as_of_date}%'
        has_decisions = _table_exists(conn, 'decision_events')
        has_signals = _table_exists(conn, 'strategy_signals')
        has_shadows = _table_exists(conn, 'shadow_positions')
        counts = {
            'signals': _scalar(conn, 'SELECT COUNT(*) FROM strategy_signals WHERE event_time LIKE ?', (day_like,)) if has_signals else 0,
            'accept': _scalar(conn, "SELECT COUNT(*) FROM decision_events WHERE decision_time LIKE ? AND action = 'accept'", (day_like,)) if has_decisions else 0,
            'reduce': _scalar(conn, "SELECT COUNT(*) FROM decision_events WHERE decision_time LIKE ? AND action = 'reduce'", (day_like,)) if has_decisions else 0,
            'delay': _scalar(conn, "SELECT COUNT(*) FROM decision_events WHERE decision_time LIKE ? AND action = 'delay'", (day_like,)) if has_decisions else 0,
            'reject': _scalar(conn, "SELECT COUNT(*) FROM decision_events WHERE decision_time LIKE ? AND action = 'reject'", (day_like,)) if has_decisions else 0,
            'shadow_opened': _scalar(conn, 'SELECT COUNT(*) FROM shadow_positions WHERE opened_at LIKE ?', (day_like,)) if has_shadows else 0,
            'shadow_closed': _scalar(conn, 'SELECT COUNT(*) FROM shadow_positions WHERE closed_at LIKE ?', (day_like,)) if has_shadows else 0,
        }
        execution_metrics = _execution_metrics(execution_db, conn, day_like)
        missed_alpha = _missed_alpha(conn, day_like)
        outcome_comparison = _outcome_comparison(execution_db, conn, day_like)
        replace_cost_analysis = _replace_cost_analysis(execution_db, day_like)
        integrity_checks = _integrity_checks(execution_db, conn, day_like)
        traceability = _traceability(execution_db, day_like)

        alert_summary = _alert_summary(execution_db, conn, day_like)
        funnel = {
            'signals': counts['signals'],
            'decision_accept_or_reduce': counts['accept'] + counts['reduce'],
            'decision_delay_or_reject': counts['delay'] + counts['reject'],
            'execution_dispatched': execution_metrics['submitted'],
            'execution_accepted': execution_metrics['accepted'],
            'execution_partial': execution_metrics['partial'],
            'execution_filled': execution_metrics['filled'],
            'execution_failed': execution_metrics['failed'],
            'execution_cancelled': execution_metrics['cancelled'],
            'execution_deduplicated': execution_metrics['deduplicated'],
            'reconciliation_strong_matched': outcome_comparison.get('strong_reconciled_trades', 0),
            'reconciliation_heuristic_matched': outcome_comparison.get('heuristic_reconciled_trades', 0),
            'shadow_opened': counts['shadow_opened'],
            'shadow_closed': counts['shadow_closed'],
            'decision_breakdown': {
                'accept': counts['accept'],
                'reduce': counts['reduce'],
                'delay': counts['delay'],
                'reject': counts['reject'],
            },
        }
        return {
            'available': True,
            'db_path': str(db),
            'execution_funnel': funnel,
            'missed_alpha': missed_alpha,
            'decision_to_fill': execution_metrics['decision_to_fill'],
            'outcome_comparison': outcome_comparison,
            'replace_cost_analysis': replace_cost_analysis,
            'integrity_checks': integrity_checks,
            'traceability': traceability,
            'alert_summary': alert_summary,
            'health_pack': {
                'overall_status': 'escalate' if alert_summary.get('severity') == 'critical' else 'attention' if alert_summary.get('severity') in {'high', 'medium'} else 'healthy',
                'recommended_actions': alert_summary.get('next_actions', []),
            },
        }
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        return bool(row)
    except sqlite3.OperationalError:
        return False


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        return 0


def _dedup_count(conn: sqlite3.Connection, decision_ids: list[str] | None = None) -> int:
    try:
        if not decision_ids:
            return 0
        placeholders = ','.join('?' for _ in decision_ids)
        row = conn.execute(
            f'''
            SELECT COUNT(*)
            FROM (
                SELECT decision_id, COUNT(DISTINCT request_hash) AS c
                FROM execution_dispatch_log
                WHERE decision_id IN ({placeholders})
                GROUP BY decision_id
                HAVING c = 1
            )
            ''',
            tuple(decision_ids),
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        return 0


def _execution_metrics(execution_db: Path, pipeline_conn: sqlite3.Connection, day_like: str) -> dict[str, Any]:
    if not execution_db.exists():
        return {'submitted': 0, 'accepted': 0, 'partial': 0, 'filled': 0, 'failed': 0, 'cancelled': 0, 'deduplicated': 0, 'decision_to_fill': {}}
    if not _table_exists(pipeline_conn, 'decision_events'):
        return {'submitted': 0, 'accepted': 0, 'partial': 0, 'filled': 0, 'failed': 0, 'cancelled': 0, 'deduplicated': 0, 'decision_to_fill': {}}
    decision_ids = [row[0] for row in pipeline_conn.execute('SELECT decision_id FROM decision_events WHERE decision_time LIKE ?', (day_like,)).fetchall()]
    if not decision_ids:
        return {'submitted': 0, 'accepted': 0, 'partial': 0, 'filled': 0, 'failed': 0, 'cancelled': 0, 'deduplicated': 0, 'decision_to_fill': {}}
    conn = sqlite3.connect(str(execution_db))
    conn.row_factory = sqlite3.Row
    try:
        placeholders = ','.join('?' for _ in decision_ids)
        params = tuple(decision_ids)
        submitted = _scalar(conn, f'SELECT COUNT(*) FROM execution_orders WHERE decision_id IN ({placeholders})', params)
        accepted = _scalar(conn, f"SELECT COUNT(*) FROM execution_orders WHERE decision_id IN ({placeholders}) AND order_status IN ('submitted','accepted','partial','filled')", params)
        partial = _scalar(conn, f"SELECT COUNT(*) FROM execution_orders WHERE decision_id IN ({placeholders}) AND order_status = 'partial'", params)
        filled = _scalar(conn, f"SELECT COUNT(*) FROM execution_orders WHERE decision_id IN ({placeholders}) AND order_status = 'filled'", params)
        failed = _scalar(conn, f"SELECT COUNT(*) FROM execution_orders WHERE decision_id IN ({placeholders}) AND order_status = 'failed'", params)
        cancelled = _scalar(conn, f"SELECT COUNT(*) FROM execution_orders WHERE decision_id IN ({placeholders}) AND order_status = 'cancelled'", params)
        deduplicated = _dedup_count(conn, decision_ids=decision_ids)
        row = conn.execute(
            f'''
            SELECT
                AVG(COALESCE(slippage_bps, 0.0)) AS avg_slippage_bps,
                SUM(COALESCE(fee_amount, 0.0)) AS total_fees,
                AVG(CASE WHEN filled_at IS NOT NULL THEN (julianday(filled_at) - julianday(submitted_at)) * 86400.0 END) AS avg_fill_seconds,
                COUNT(CASE WHEN filled_at IS NOT NULL THEN 1 END) AS filled_count
            FROM execution_orders
            WHERE decision_id IN ({placeholders})
            ''',
            params,
        ).fetchone()
        return {
            'submitted': submitted,
            'accepted': accepted,
            'partial': partial,
            'filled': filled,
            'failed': failed,
            'cancelled': cancelled,
            'deduplicated': deduplicated,
            'decision_to_fill': {
                'filled_orders': int(row['filled_count'] or 0),
                'fill_rate_vs_dispatched': round((filled / submitted), 4) if submitted else 0.0,
                'avg_slippage_bps': round(float(row['avg_slippage_bps'] or 0.0), 4),
                'total_execution_fees': round(float(row['total_fees'] or 0.0), 8),
                'avg_fill_seconds': round(float(row['avg_fill_seconds'] or 0.0), 4),
            },
        }
    except sqlite3.OperationalError:
        return {'submitted': 0, 'accepted': 0, 'partial': 0, 'filled': 0, 'failed': 0, 'cancelled': 0, 'deduplicated': 0, 'decision_to_fill': {}}
    finally:
        conn.close()


def _missed_alpha(conn: sqlite3.Connection, day_like: str) -> dict[str, Any]:
    if not (_table_exists(conn, 'shadow_positions') and _table_exists(conn, 'decision_events') and _table_exists(conn, 'strategy_signals')):
        return {
            'total_rejected_shadow': 0, 'profitable_rejected_shadow': 0, 'profitable_rejected_ratio': 0.0,
            'avg_profitable_rejected_ratio': 0.0, 'best_rejected_ratio': 0.0, 'total_rejected_shadow_pnl_ratio': 0.0, 'strategy_missed_alpha_rank': [],
        }
    try:
        row = conn.execute(
            '''
            SELECT
                COUNT(*) AS total_rejected_shadow,
                SUM(CASE WHEN COALESCE(sp.pnl_ratio, 0.0) > 0 THEN 1 ELSE 0 END) AS profitable_rejected_shadow,
                AVG(CASE WHEN COALESCE(sp.pnl_ratio, 0.0) > 0 THEN sp.pnl_ratio END) AS avg_profitable_rejected_ratio,
                MAX(COALESCE(sp.pnl_ratio, 0.0)) AS best_rejected_ratio,
                SUM(COALESCE(sp.pnl_ratio, 0.0)) AS total_rejected_shadow_pnl_ratio
            FROM shadow_positions sp
            JOIN decision_events d ON d.decision_id = sp.decision_id
            WHERE d.action IN ('reject', 'delay')
              AND sp.opened_at LIKE ?
            ''',
            (day_like,),
        ).fetchone()
        ranking = [
            dict(r)
            for r in conn.execute(
                '''
                SELECT
                    s.strategy_name,
                    COUNT(*) AS rejected_count,
                    SUM(CASE WHEN COALESCE(sp.pnl_ratio, 0.0) > 0 THEN 1 ELSE 0 END) AS profitable_count,
                    AVG(COALESCE(sp.pnl_ratio, 0.0)) AS avg_pnl_ratio,
                    MAX(COALESCE(sp.pnl_ratio, 0.0)) AS best_pnl_ratio
                FROM shadow_positions sp
                JOIN decision_events d ON d.decision_id = sp.decision_id
                JOIN strategy_signals s ON s.signal_id = sp.signal_id
                WHERE d.action IN ('reject', 'delay')
                  AND sp.opened_at LIKE ?
                GROUP BY s.strategy_name
                ORDER BY avg_pnl_ratio DESC, profitable_count DESC, rejected_count DESC
                LIMIT 5
                ''',
                (day_like,),
            ).fetchall()
        ]
        total = int(row['total_rejected_shadow'] or 0)
        profitable = int(row['profitable_rejected_shadow'] or 0)
        return {
            'total_rejected_shadow': total,
            'profitable_rejected_shadow': profitable,
            'profitable_rejected_ratio': round((profitable / total), 4) if total else 0.0,
            'avg_profitable_rejected_ratio': round(float(row['avg_profitable_rejected_ratio'] or 0.0), 4),
            'best_rejected_ratio': round(float(row['best_rejected_ratio'] or 0.0), 4),
            'total_rejected_shadow_pnl_ratio': round(float(row['total_rejected_shadow_pnl_ratio'] or 0.0), 4),
            'strategy_missed_alpha_rank': [
                {
                    'strategy_name': r['strategy_name'],
                    'rejected_count': int(r['rejected_count'] or 0),
                    'profitable_count': int(r['profitable_count'] or 0),
                    'avg_pnl_ratio': round(float(r['avg_pnl_ratio'] or 0.0), 4),
                    'best_pnl_ratio': round(float(r['best_pnl_ratio'] or 0.0), 4),
                }
                for r in ranking
            ],
        }
    except sqlite3.OperationalError:
        return {
            'total_rejected_shadow': 0,
            'profitable_rejected_shadow': 0,
            'profitable_rejected_ratio': 0.0,
            'avg_profitable_rejected_ratio': 0.0,
            'best_rejected_ratio': 0.0,
            'total_rejected_shadow_pnl_ratio': 0.0,
            'strategy_missed_alpha_rank': [],
        }


def _outcome_comparison(execution_db: Path, pipeline_conn: sqlite3.Connection, day_like: str) -> dict[str, Any]:
    if not execution_db.exists() or not (_table_exists(pipeline_conn, 'decision_events') and _table_exists(pipeline_conn, 'shadow_positions')):
        return {}
    conn = sqlite3.connect(str(execution_db))
    conn.row_factory = sqlite3.Row
    try:
        accepted_decision_ids = [row[0] for row in pipeline_conn.execute("SELECT decision_id FROM decision_events WHERE decision_time LIKE ? AND action IN ('accept','reduce')", (day_like,)).fetchall()]
        rejected_shadow = pipeline_conn.execute(
            '''
            SELECT COUNT(*) AS cnt, AVG(COALESCE(sp.pnl_ratio, 0.0)) AS avg_ratio, SUM(COALESCE(sp.pnl_ratio, 0.0)) AS total_ratio
            FROM shadow_positions sp
            JOIN decision_events d ON d.decision_id = sp.decision_id
            WHERE d.decision_time LIKE ? AND d.action IN ('reject', 'delay')
            ''',
            (day_like,),
        ).fetchone()
        result = {
            'accepted_decisions': len(accepted_decision_ids),
            'accepted_filled_orders': 0,
            'accepted_reconciled_trades': 0,
            'strong_reconciled_trades': 0,
            'heuristic_reconciled_trades': 0,
            'accepted_trade_pnl_usd': 0.0,
            'accepted_trade_avg_ratio': 0.0,
            'accepted_avg_slippage_bps': 0.0,
            'rejected_shadow_count': int(rejected_shadow['cnt'] or 0),
            'rejected_shadow_avg_ratio': round(float(rejected_shadow['avg_ratio'] or 0.0), 4),
            'rejected_shadow_total_ratio': round(float(rejected_shadow['total_ratio'] or 0.0), 4),
            'actual_vs_rejected_shadow_ratio_gap': 0.0,
        }
        if not accepted_decision_ids:
            return result
        placeholders = ','.join('?' for _ in accepted_decision_ids)
        params = tuple(accepted_decision_ids)
        fills = conn.execute(
            f"SELECT COUNT(*) AS filled_orders, AVG(COALESCE(slippage_bps, 0.0)) AS avg_slippage FROM execution_orders WHERE decision_id IN ({placeholders}) AND order_status = 'filled'",
            params,
        ).fetchone()
        result['accepted_filled_orders'] = int(fills['filled_orders'] or 0)
        result['accepted_avg_slippage_bps'] = round(float(fills['avg_slippage'] or 0.0), 4)
        try:
            recon = conn.execute(
                f'''
                SELECT COUNT(*) AS trade_count,
                       SUM(COALESCE(trade_profit_abs, 0.0)) AS pnl_usd,
                       AVG(COALESCE(trade_profit_ratio, 0.0)) AS avg_ratio,
                       SUM(CASE WHEN match_type = 'strong_key' THEN 1 ELSE 0 END) AS strong_count,
                       SUM(CASE WHEN match_type != 'strong_key' THEN 1 ELSE 0 END) AS heuristic_count
                FROM execution_trade_reconciliation
                WHERE decision_id IN ({placeholders})
                ''',
                params,
            ).fetchone()
            result['accepted_reconciled_trades'] = int(recon['trade_count'] or 0)
            result['strong_reconciled_trades'] = int(recon['strong_count'] or 0)
            result['heuristic_reconciled_trades'] = int(recon['heuristic_count'] or 0)
            result['accepted_trade_pnl_usd'] = round(float(recon['pnl_usd'] or 0.0), 4)
            result['accepted_trade_avg_ratio'] = round(float(recon['avg_ratio'] or 0.0), 4)
            result['actual_vs_rejected_shadow_ratio_gap'] = round(result['accepted_trade_avg_ratio'] - result['rejected_shadow_avg_ratio'], 4)
        except sqlite3.OperationalError:
            pass
        return result
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _replace_cost_analysis(execution_db: Path, day_like: str) -> dict[str, Any]:
    if not execution_db.exists():
        return {}
    conn = sqlite3.connect(str(execution_db))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            '''
            SELECT
                COUNT(*) AS replace_orders,
                AVG(COALESCE(slippage_bps, 0.0)) AS avg_replace_slippage_bps,
                SUM(COALESCE(fee_amount, 0.0)) AS total_replace_fees,
                AVG(CASE WHEN parent_order_id IS NOT NULL AND requested_price > 0 AND average_fill_price IS NOT NULL
                    THEN ABS(average_fill_price - requested_price) / requested_price * 10000.0 END) AS avg_replace_price_move_bps
            FROM execution_orders
            WHERE submitted_at LIKE ?
              AND parent_order_id IS NOT NULL
            ''',
            (day_like,),
        ).fetchone()
        by_reason = [
            {
                'replace_reason': r['replace_reason'] or 'unknown',
                'count': int(r['cnt'] or 0),
                'avg_slippage_bps': round(float(r['avg_slippage_bps'] or 0.0), 4),
                'total_fees': round(float(r['total_fees'] or 0.0), 8),
            }
            for r in conn.execute(
                '''
                SELECT replace_reason, COUNT(*) AS cnt, AVG(COALESCE(slippage_bps, 0.0)) AS avg_slippage_bps, SUM(COALESCE(fee_amount, 0.0)) AS total_fees
                FROM execution_orders
                WHERE submitted_at LIKE ? AND parent_order_id IS NOT NULL
                GROUP BY replace_reason
                ORDER BY cnt DESC, total_fees DESC
                ''',
                (day_like,),
            ).fetchall()
        ]
        return {
            'replace_orders': int(row['replace_orders'] or 0),
            'avg_replace_slippage_bps': round(float(row['avg_replace_slippage_bps'] or 0.0), 4),
            'total_replace_fees': round(float(row['total_replace_fees'] or 0.0), 8),
            'avg_replace_price_move_bps': round(float(row['avg_replace_price_move_bps'] or 0.0), 4),
            'replace_by_reason': by_reason,
        }
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()



def _integrity_checks(execution_db: Path, pipeline_conn: sqlite3.Connection, day_like: str) -> dict[str, Any]:
    if not execution_db.exists():
        return {}
    conn = sqlite3.connect(str(execution_db))
    conn.row_factory = sqlite3.Row
    try:
        decision_ids = [row[0] for row in pipeline_conn.execute('SELECT decision_id FROM decision_events WHERE decision_time LIKE ?', (day_like,)).fetchall()] if _table_exists(pipeline_conn, 'decision_events') else []
        signal_ids = [row[0] for row in pipeline_conn.execute('SELECT signal_id FROM strategy_signals WHERE event_time LIKE ?', (day_like,)).fetchall()] if _table_exists(pipeline_conn, 'strategy_signals') else []
        placeholders_d = ','.join('?' for _ in decision_ids) if decision_ids else ''
        placeholders_s = ','.join('?' for _ in signal_ids) if signal_ids else ''
        duplicate_dispatches = 0
        orphan_orders = 0
        filled_unreconciled = 0
        if decision_ids:
            duplicate_dispatches = _scalar(conn, f'SELECT COUNT(*) FROM (SELECT decision_id FROM execution_dispatch_log WHERE decision_id IN ({placeholders_d}) GROUP BY decision_id, request_hash HAVING COUNT(*) > 1)', tuple(decision_ids))
            orphan_orders = _scalar(conn, f'SELECT COUNT(*) FROM execution_orders WHERE decision_id NOT IN ({placeholders_d})', tuple(decision_ids))
            filled_unreconciled = _scalar(conn, f"SELECT COUNT(*) FROM execution_orders eo LEFT JOIN execution_trade_reconciliation r ON r.order_id = eo.order_id WHERE eo.decision_id IN ({placeholders_d}) AND eo.order_status = 'filled' AND r.order_id IS NULL", tuple(decision_ids))
        orphan_dispatch_signals = 0
        if signal_ids:
            orphan_dispatch_signals = _scalar(conn, f'SELECT COUNT(*) FROM execution_dispatch_log WHERE signal_id NOT IN ({placeholders_s})', tuple(signal_ids))
        state_anomalies = []
        try:
            from services.execution.execution_store import ExecutionStore
            state_anomalies = ExecutionStore(execution_db).list_state_anomalies()
        except Exception:
            state_anomalies = []
        return {
            'duplicate_dispatches': duplicate_dispatches,
            'orphan_orders': orphan_orders,
            'orphan_dispatch_signals': orphan_dispatch_signals,
            'filled_unreconciled_orders': filled_unreconciled,
            'state_anomalies': state_anomalies[:10],
            'state_anomaly_count': len(state_anomalies),
        }
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _traceability(execution_db: Path, day_like: str, pipeline_db: Path | None = None) -> dict[str, Any]:
    if not execution_db.exists():
        return {}
    conn = sqlite3.connect(str(execution_db))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            '''
            SELECT
                COUNT(*) AS orders,
                SUM(CASE WHEN run_id IS NOT NULL AND trace_id IS NOT NULL THEN 1 ELSE 0 END) AS traced_orders,
                COUNT(DISTINCT run_id) AS runs,
                COUNT(DISTINCT trace_id) AS traces
            FROM execution_orders
            WHERE submitted_at LIKE ?
            ''',
            (day_like,),
        ).fetchone()
        traced = int(row['traced_orders'] or 0)
        total = int(row['orders'] or 0)
        result = {
            'orders': total,
            'traced_orders': traced,
            'trace_coverage_ratio': round((traced / total), 4) if total else 0.0,
            'distinct_runs': int(row['runs'] or 0),
            'distinct_traces': int(row['traces'] or 0),
        }
        if pipeline_db and pipeline_db.exists():
            result['pipeline_tables'] = trace_coverage(pipeline_db, day_like[:10])
        return result
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()



def _alert_summary(execution_db: Path, pipeline_conn: sqlite3.Connection, day_like: str) -> dict[str, Any]:
    from services.control.incident_response import build_next_actions, enrich_incidents, summarize_disposition

    incidents: list[dict[str, Any]] = []
    if execution_db.exists():
        exe = sqlite3.connect(str(execution_db))
        exe.row_factory = sqlite3.Row
        try:
            filled_unreconciled = _scalar(exe, "SELECT COUNT(*) FROM execution_orders eo LEFT JOIN execution_trade_reconciliation r ON r.order_id = eo.order_id WHERE eo.order_status='filled' AND r.order_id IS NULL", ())
            if filled_unreconciled:
                incidents.append({'severity': 'high', 'code': 'filled_unreconciled_orders', 'message': f'{filled_unreconciled} filled orders have no reconciliation row'})
            duplicate_dispatches = _scalar(exe, 'SELECT COUNT(*) FROM (SELECT decision_id, request_hash FROM execution_dispatch_log GROUP BY decision_id, request_hash HAVING COUNT(*) > 1)', ())
            if duplicate_dispatches:
                incidents.append({'severity': 'medium', 'code': 'duplicate_dispatches', 'message': f'{duplicate_dispatches} duplicate dispatch rows found'})
        finally:
            exe.close()
    db_path = Path(pipeline_conn.execute('PRAGMA database_list').fetchone()[2])
    coverage = trace_coverage(db_path, day_like[:10] if day_like else None)
    low_trace_tables = [f"{name}={info['ratio']:.2%}" for name, info in coverage['tables'].items() if info['rows'] and info['ratio'] < 1.0]
    if low_trace_tables:
        incidents.append({'severity': 'medium', 'code': 'pipeline_trace_gap', 'message': 'trace coverage below 100% for ' + ', '.join(low_trace_tables)})
    incidents = enrich_incidents(incidents)
    severity = 'critical' if any(i['severity'] == 'high' for i in incidents) and len(incidents) >= 2 else 'high' if any(i['severity'] == 'high' for i in incidents) else 'medium' if incidents else 'ok'
    return {
        'severity': severity,
        'alert_count': len(incidents),
        'incidents': incidents,
        'disposition': summarize_disposition(incidents),
        'next_actions': build_next_actions(incidents),
    }
