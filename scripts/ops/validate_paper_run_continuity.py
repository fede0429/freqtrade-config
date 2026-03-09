#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.control.paper_run_validator import validate_paper_run_continuity


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate continuity of archived paper-run evidence packs.')
    parser.add_argument('--evidence-root', required=True)
    parser.add_argument('--expected-days', type=int, default=7)
    parser.add_argument('--output-json')
    parser.add_argument('--output-md')
    args = parser.parse_args()

    result = validate_paper_run_continuity(args.evidence_root, expected_days=args.expected_days)
    payload = {
        'evidence_root': result.evidence_root,
        'days_completed': result.days_completed,
        'expected_days': result.expected_days,
        'missing_days': result.missing_days,
        'duplicate_days': result.duplicate_days,
        'guard_fail_days': result.guard_fail_days,
        'startup_not_armed_days': result.startup_not_armed_days,
        'release_not_approved_days': result.release_not_approved_days,
        'scanner_not_live_days': result.scanner_not_live_days,
        'is_contiguous': result.is_contiguous,
        'has_failures': result.has_failures,
        'manifests': result.manifests,
    }

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    if args.output_md:
        lines = [
            '# Paper Run Continuity Check',
            '',
            f"- Evidence root: {result.evidence_root}",
            f"- Days completed: {result.days_completed}/{result.expected_days}",
            f"- Contiguous: {result.is_contiguous}",
            f"- Failures present: {result.has_failures}",
            '',
            '## Findings',
            f"- Missing days: {result.missing_days or 'none'}",
            f"- Guard fail days: {result.guard_fail_days or 'none'}",
            f"- Startup not armed days: {result.startup_not_armed_days or 'none'}",
            f"- Release not approved days: {result.release_not_approved_days or 'none'}",
            f"- Scanner not live days: {result.scanner_not_live_days or 'none'}",
            '',
        ]
        Path(args.output_md).write_text('\n'.join(lines), encoding='utf-8')

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
