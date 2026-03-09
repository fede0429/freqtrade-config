from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


import argparse
import json
from pathlib import Path

from services.control.program_state import build_program_state


def render_markdown(payload: dict) -> str:
    lines = [
        f"# Program Status - {payload['as_of']}",
        '',
        f"- Overall status: {payload['overall_status']}",
        '',
        '## Milestones',
    ]
    for item in payload['milestones']:
        lines.append(f"### {item['name']}")
        lines.append(f"- Status: {item['status']}")
        if item.get('details'):
            for key, value in item['details'].items():
                lines.append(f"- {key}: {value}")
        if item.get('evidence'):
            lines.append(f"- Evidence: {', '.join(item['evidence'])}")
        if item.get('next_actions'):
            lines.append('- Next actions:')
            for action in item['next_actions']:
                lines.append(f"  - {action}")
        lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description='Render overall studio program status')
    parser.add_argument('--preflight', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--scanner', required=True)
    parser.add_argument('--startup-bundle')
    parser.add_argument('--evidence-root')
    parser.add_argument('--continuity')
    parser.add_argument('--scorecard')
    parser.add_argument('--budget-guard')
    parser.add_argument('--rollback-manifest')
    parser.add_argument('--output', required=True)
    parser.add_argument('--markdown-output')
    args = parser.parse_args()

    state = build_program_state(
        args.preflight,
        args.report,
        args.scanner,
        args.startup_bundle,
        args.evidence_root,
        args.continuity,
        args.scorecard,
        args.budget_guard,
        args.rollback_manifest,
    )

    payload = {
        'as_of': state.as_of,
        'overall_status': state.overall_status,
        'milestones': [
            {
                'name': m.name,
                'status': m.status,
                'evidence': m.evidence,
                'next_actions': m.next_actions,
                'details': m.details,
            }
            for m in state.milestones
        ],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.markdown_output:
        md = Path(args.markdown_output)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(render_markdown(payload), encoding='utf-8')
    print(json.dumps({'output': str(output), 'overall_status': payload['overall_status']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
