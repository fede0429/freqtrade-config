from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from services.control.canary_budget_guard import evaluate_canary_budget_guard


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--canary-profile', required=True)
    parser.add_argument('--readiness-pack', required=True)
    parser.add_argument('--daily-report', required=True)
    parser.add_argument('--startup-bundle', required=True)
    parser.add_argument('--preflight', required=True)
    parser.add_argument('--output-json', required=True)
    parser.add_argument('--output-md', required=True)
    args = parser.parse_args()

    result = evaluate_canary_budget_guard(
        canary_profile_path=args.canary_profile,
        readiness_pack_manifest_path=args.readiness_pack,
        daily_report_path=args.daily_report,
        startup_bundle_path=args.startup_bundle,
        preflight_path=args.preflight,
    )
    payload = asdict(result)
    with open(args.output_json, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    lines = [
        '# Canary Budget Guard',
        '',
        f"- Status: {result.status}",
        f"- Verdict: {result.verdict}",
        f"- Checks passed: {result.summary['checks_passed']}/{result.summary['checks_total']}",
        '',
        '## Failed Checks',
    ]
    failed = [c for c in result.checks if not c['passed']]
    if failed:
        for c in failed:
            lines.append(f"- {c['name']}: {c['details']}")
    else:
        lines.append('- None')
    lines.extend(['', '## Required Actions'])
    for action in result.required_actions:
        lines.append(f'- [ ] {action}')
    with open(args.output_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"budget guard status={result.status} verdict={result.verdict}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
