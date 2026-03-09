#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution.execution_store import ExecutionStore
from services.execution.pipeline_trace import trace_coverage
from services.control.incident_response import build_next_actions, enrich_incidents, summarize_disposition


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Render signal pipeline alerts and incident summary.')
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


def render_md(alerts: dict[str, Any]) -> str:
    sev = alerts['severity']
    lines = [
        '# Signal Pipeline Incident Summary',
        '',
        f"- Severity: {sev}",
        f"- Alert count: {alerts['alert_count']}",
        f"- As of date: {alerts.get('as_of_date') or 'all'}",
        f"- Disposition: {alerts.get('disposition', {}).get('status', 'clear')}",
        '',
        '## Incidents',
    ]
    if alerts['incidents']:
        for item in alerts['incidents']:
            lines.append(f"- [{item['severity'].upper()}] {item['code']}: {item['summary']}")
            lines.append(f"  - Owner: {item.get('owner', 'platform')}")
            lines.append(f"  - Auto repairable: {bool(item.get('auto_repairable'))}")
            if item.get('recommended_script'):
                lines.append(f"  - Suggested command: `{item['recommended_script']}`")
            for step in item.get('remediation_steps', []):
                lines.append(f"  - Step: {step}")
    else:
        lines.append('- none')
    lines.extend(['', '## Next Actions'])
    for action in alerts.get('next_actions', []):
        lines.append(f'- {action}')
    return '\n'.join(lines) + '\n'


def main() -> int:
    args = parse_args()
    pipe_db = Path(args.signal_pipeline_db)
    exec_db = Path(args.execution_db)
    if not pipe_db.exists() or not exec_db.exists():
        raise FileNotFoundError('db not found')

    exe = sqlite3.connect(str(exec_db))
    exe.row_factory = sqlite3.Row
    try:
        incidents: list[dict[str, Any]] = []
        filled_unreconciled = _scalar(exe, "SELECT COUNT(*) FROM execution_orders eo LEFT JOIN execution_trade_reconciliation r ON r.order_id = eo.order_id WHERE eo.order_status='filled' AND r.order_id IS NULL")
        if filled_unreconciled:
            incidents.append({'severity': 'high', 'code': 'filled_unreconciled_orders', 'message': f'{filled_unreconciled} filled orders have no reconciliation row'})
        state_anomalies = len(ExecutionStore(exec_db).list_state_anomalies())
        if state_anomalies:
            incidents.append({'severity': 'high', 'code': 'execution_state_anomalies', 'message': f'{state_anomalies} execution orders have invalid state transitions'})
        duplicate_dispatches = _scalar(exe, 'SELECT COUNT(*) FROM (SELECT decision_id, request_hash FROM execution_dispatch_log GROUP BY decision_id, request_hash HAVING COUNT(*) > 1)')
        if duplicate_dispatches:
            incidents.append({'severity': 'medium', 'code': 'duplicate_dispatches', 'message': f'{duplicate_dispatches} duplicate dispatch rows found'})
        coverage = trace_coverage(pipe_db, args.as_of_date)
        low_trace_tables = [f"{name}={info['ratio']:.2%}" for name, info in coverage['tables'].items() if info['rows'] and info['ratio'] < 1.0]
        if low_trace_tables:
            incidents.append({'severity': 'medium', 'code': 'pipeline_trace_gap', 'message': 'trace coverage below 100% for ' + ', '.join(low_trace_tables)})
        incidents = enrich_incidents(incidents)
        severity = 'critical' if any(i['severity'] == 'high' for i in incidents) and len(incidents) >= 2 else 'high' if any(i['severity'] == 'high' for i in incidents) else 'medium' if incidents else 'ok'
        result = {
            'severity': severity,
            'alert_count': len(incidents),
            'as_of_date': args.as_of_date,
            'incidents': incidents,
            'trace_coverage': coverage,
            'disposition': summarize_disposition(incidents),
            'next_actions': build_next_actions(incidents),
        }
        if args.output_json:
            Path(args.output_json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        if args.output_md:
            Path(args.output_md).write_text(render_md(result), encoding='utf-8')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        exe.close()


if __name__ == '__main__':
    raise SystemExit(main())
