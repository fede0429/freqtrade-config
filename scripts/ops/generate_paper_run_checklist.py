from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate 7-day paper run checklist from program status')
    parser.add_argument('--program-status', required=True)
    parser.add_argument('--output-json', required=True)
    parser.add_argument('--output-md', required=True)
    args = parser.parse_args()

    status = load_json(args.program_status)
    milestones = {item['name']: item for item in status.get('milestones', [])}
    scanner = milestones.get('market_intelligence', {})
    reporting = milestones.get('operations_reporting', {})
    startup = milestones.get('startup_chain', {})

    checklist = {
        'as_of': status.get('as_of'),
        'overall_status': status.get('overall_status'),
        'goal': 'complete 7 consecutive paper-trading days before canary promotion',
        'entry_criteria': [
            'release gate approved for paper',
            'startup chain is armed',
            'reporting input type is sqlite',
            'scanner output produces at least 2 tradable pairs',
        ],
        'current_observations': {
            'scanner_source_mode': scanner.get('details', {}).get('source_mode'),
            'pnl_input_type': reporting.get('details', {}).get('pnl_input_type'),
            'startup_mode': startup.get('details', {}).get('startup_mode'),
        },
        'daily_checkpoints': [
            {'day': 1, 'focus': 'baseline health', 'checks': ['archive scanner report', 'archive daily report', 'archive preflight/startup bundle', 'confirm guard_status is healthy']},
            {'day': 2, 'focus': 'signal stability', 'checks': ['compare tradable_pairs with day 1', 'review scanner risk flags drift', 'note any manual overrides']},
            {'day': 3, 'focus': 'strategy consistency', 'checks': ['review active strategy exposures', 'check unexpected candidate activity', 'confirm no blocked strategy receives budget']},
            {'day': 4, 'focus': 'drawdown control', 'checks': ['track current_drawdown_ratio', 'confirm no release gate regressions', 'review losing trades for repeated patterns']},
            {'day': 5, 'focus': 'ops discipline', 'checks': ['verify every startup went through startup_gate', 'ensure evidence bundle is complete', 'refresh program status']},
            {'day': 6, 'focus': 'promotion readiness', 'checks': ['compare realized pnl by strategy', 'review scanner source health', 'prepare canary scorecard notes']},
            {'day': 7, 'focus': 'go or hold decision', 'checks': ['summarize 7-day pnl', 'summarize risk events', 'decide promote/hold/downgrade and record rationale']},
        ],
        'exit_criteria': [
            '7 consecutive days completed with archived evidence',
            'no blocked startup days',
            'risk guard remained healthy or every exception has documented remediation',
            'owner decision recorded for canary promotion or hold',
        ],
    }

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(checklist, indent=2, ensure_ascii=False), encoding='utf-8')

    lines = [
        f"# 7-Day Paper Run Checklist - {checklist['as_of']}",
        '',
        f"- Overall status: {checklist['overall_status']}",
        f"- Goal: {checklist['goal']}",
        '',
        '## Entry Criteria',
    ]
    for item in checklist['entry_criteria']:
        lines.append(f'- {item}')
    lines.extend(['', '## Current Observations'])
    for key, value in checklist['current_observations'].items():
        lines.append(f'- {key}: {value}')
    lines.extend(['', '## Daily Checkpoints'])
    for item in checklist['daily_checkpoints']:
        lines.append(f"### Day {item['day']} - {item['focus']}")
        for check in item['checks']:
            lines.append(f'- [ ] {check}')
        lines.append('')
    lines.append('## Exit Criteria')
    for item in checklist['exit_criteria']:
        lines.append(f'- {item}')

    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'wrote {out_json}')
    print(f'wrote {out_md}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
