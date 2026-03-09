from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.control.canary_readiness_pack import build_canary_readiness_pack


def main() -> int:
    parser = argparse.ArgumentParser(description='Build canary readiness pack from current evidence and scorecard')
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--program-status', required=True)
    parser.add_argument('--continuity', required=True)
    parser.add_argument('--scorecard', required=True)
    parser.add_argument('--evidence-root', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--paper-run-checklist')
    parser.add_argument('--startup-bundle')
    parser.add_argument('--preflight')
    args = parser.parse_args()

    result = build_canary_readiness_pack(
        output_root=args.output_root,
        as_of=args.as_of,
        program_status_path=args.program_status,
        continuity_path=args.continuity,
        scorecard_path=args.scorecard,
        evidence_root=args.evidence_root,
        paper_run_checklist_path=args.paper_run_checklist,
        startup_bundle_path=args.startup_bundle,
        preflight_path=args.preflight,
    )

    payload = {
        'pack_dir': str(result.pack_dir),
        'manifest_path': str(result.manifest_path),
        'summary_path': str(result.summary_path),
        'copied_files': result.copied_files,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
