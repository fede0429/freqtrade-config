#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.control.paper_run_validator import build_canary_promotion_scorecard, validate_paper_run_continuity


def main() -> int:
    parser = argparse.ArgumentParser(description='Render canary promotion scorecard from paper-run evidence.')
    parser.add_argument('--evidence-root', required=True)
    parser.add_argument('--expected-days', type=int, default=7)
    parser.add_argument('--output-json', required=True)
    parser.add_argument('--output-md', required=True)
    parser.add_argument('--allow-non-live-scanner', action='store_true')
    args = parser.parse_args()

    continuity = validate_paper_run_continuity(args.evidence_root, expected_days=args.expected_days)
    card = build_canary_promotion_scorecard(
        continuity,
        min_days=args.expected_days,
        require_live_scanner=not args.allow_non_live_scanner,
    )
    payload = {
        'status': card.status,
        'score': card.score,
        'max_score': card.max_score,
        'verdict': card.verdict,
        'checks': card.checks,
        'required_actions': card.required_actions,
        'summary': card.summary,
    }
    Path(args.output_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = [
        '# Canary Promotion Scorecard',
        '',
        f"- Status: {card.status}",
        f"- Verdict: {card.verdict}",
        f"- Score: {card.score}/{card.max_score}",
        '',
        '## Checks',
    ]
    for check in card.checks:
        lines.append(f"- {'PASS' if check['passed'] else 'FAIL'} {check['name']}")
    lines.extend(['', '## Required Actions'])
    if card.required_actions:
        lines.extend([f'- {item}' for item in card.required_actions])
    else:
        lines.append('- none')
    Path(args.output_md).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
