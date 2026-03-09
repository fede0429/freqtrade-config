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

from services.analytics.signal_pipeline_loader import load_signal_pipeline_summary
from services.control.incident_response import build_next_actions
from services.execution.pipeline_trace import trace_coverage


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Build a daily close health pack for the signal pipeline.')
    p.add_argument('--signal-pipeline-db', required=True)
    p.add_argument('--execution-db', required=True)
    p.add_argument('--as-of-date', default=None)
    p.add_argument('--output-json', required=True)
    p.add_argument('--output-md', required=True)
    return p.parse_args()


def _stability(execution_db: Path, signal_pipeline_db: Path, as_of_date: str | None) -> dict[str, Any]:
    exe = sqlite3.connect(str(execution_db))
    exe.row_factory = sqlite3.Row
    try:
        dup = exe.execute('SELECT COUNT(*) FROM (SELECT decision_id, request_hash FROM execution_dispatch_log GROUP BY decision_id, request_hash HAVING COUNT(*) > 1)').fetchone()[0]
        orun = exe.execute("SELECT COUNT(*) FROM execution_orders eo LEFT JOIN execution_trade_reconciliation r ON r.order_id = eo.order_id WHERE eo.order_status='filled' AND r.order_id IS NULL").fetchone()[0]
        traced = exe.execute('SELECT COUNT(*) AS n, SUM(CASE WHEN run_id IS NOT NULL AND trace_id IS NOT NULL THEN 1 ELSE 0 END) AS t FROM execution_orders').fetchone()
        cov = round(float(traced['t'] or 0) / float(traced['n'] or 1), 4) if traced['n'] else 1.0
    finally:
        exe.close()
    pipe_cov = trace_coverage(signal_pipeline_db, as_of_date)
    score = 100 - int(dup) * 10 - int(orun) * 10 - int(max(0, 1 - cov) * 20)
    status = 'healthy' if score >= 90 else 'watch' if score >= 75 else 'degraded'
    return {
        'score': score,
        'status': status,
        'duplicate_dispatches': int(dup),
        'filled_unreconciled_orders': int(orun),
        'execution_trace_coverage': cov,
        'pipeline_trace_coverage': pipe_cov,
    }


def render_md(pack: dict[str, Any]) -> str:
    lines = [
        '# Daily Close Health Pack',
        '',
        f"- As of date: {pack.get('as_of_date') or 'all'}",
        f"- Overall status: {pack['overall_status']}",
        f"- Stability score: {pack['stability']['score']}",
        '',
        '## Top Alerts',
    ]
    incidents = pack.get('alerts', {}).get('incidents', [])
    if incidents:
        for item in incidents[:5]:
            lines.append(f"- [{item['severity'].upper()}] {item['code']}: {item['summary']}")
    else:
        lines.append('- none')
    lines.extend(['', '## Recommended Actions'])
    for action in pack.get('recommended_actions', []):
        lines.append(f'- {action}')
    lines.extend(['', '## Replay Entry Points'])
    for item in pack.get('replay_commands', []):
        lines.append(f'- `{item}`')
    return '\n'.join(lines) + '\n'


def _derive_replay_commands(signal_pipeline_db: Path, execution_db: Path, as_of_date: str | None) -> list[str]:
    cmds: list[str] = []
    pipe = sqlite3.connect(str(signal_pipeline_db))
    pipe.row_factory = sqlite3.Row
    exe = sqlite3.connect(str(execution_db))
    exe.row_factory = sqlite3.Row
    try:
        row = exe.execute("SELECT order_id, decision_id, signal_id FROM execution_orders ORDER BY submitted_at DESC LIMIT 1").fetchone()
        if row:
            if row['order_id']:
                cmds.append(f"python apps/execution/replay_execution_trace.py --execution-db {execution_db} --signal-pipeline-db {signal_pipeline_db} --order-id {row['order_id']}")
            if row['decision_id']:
                cmds.append(f"python apps/execution/replay_execution_trace.py --execution-db {execution_db} --signal-pipeline-db {signal_pipeline_db} --decision-id {row['decision_id']}")
            if row['signal_id']:
                cmds.append(f"python apps/execution/replay_execution_trace.py --execution-db {execution_db} --signal-pipeline-db {signal_pipeline_db} --signal-id {row['signal_id']}")
    finally:
        pipe.close()
        exe.close()
    return cmds


def main() -> int:
    args = parse_args()
    signal_pipeline = load_signal_pipeline_summary(args.signal_pipeline_db, args.as_of_date or '', args.execution_db)
    alerts = signal_pipeline.get('alert_summary', {})
    stability = _stability(Path(args.execution_db), Path(args.signal_pipeline_db), args.as_of_date)
    overall_status = 'healthy'
    if alerts.get('severity') in {'high', 'critical'} or stability['status'] != 'healthy':
        overall_status = 'attention'
    if alerts.get('severity') == 'critical' or stability['status'] == 'degraded':
        overall_status = 'escalate'
    pack = {
        'as_of_date': args.as_of_date,
        'overall_status': overall_status,
        'stability': stability,
        'alerts': alerts,
        'signal_pipeline': signal_pipeline,
        'recommended_actions': build_next_actions(alerts.get('incidents', [])),
        'replay_commands': _derive_replay_commands(Path(args.signal_pipeline_db), Path(args.execution_db), args.as_of_date),
    }
    Path(args.output_json).write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding='utf-8')
    Path(args.output_md).write_text(render_md(pack), encoding='utf-8')
    print(json.dumps({'overall_status': overall_status, 'alert_count': alerts.get('alert_count', 0), 'stability_score': stability['score']}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
