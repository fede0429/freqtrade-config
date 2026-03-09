from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.control.evidence_pack import archive_paper_run_day


def main() -> int:
    parser = argparse.ArgumentParser(description='Archive one paper-run evidence pack')
    parser.add_argument('--program-status', required=True)
    parser.add_argument('--scanner', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--preflight', required=True)
    parser.add_argument('--startup-bundle', required=True)
    parser.add_argument('--evidence-root', required=True)
    parser.add_argument('--day', type=int)
    args = parser.parse_args()

    result = archive_paper_run_day(
        evidence_root=args.evidence_root,
        program_status_path=args.program_status,
        scanner_path=args.scanner,
        report_path=args.report,
        preflight_path=args.preflight,
        startup_bundle_path=args.startup_bundle,
        day=args.day,
    )

    payload = {
        'day': result.day,
        'archive_dir': str(result.archive_dir),
        'manifest_path': str(result.manifest_path),
        'summary_path': str(result.summary_path),
        'copied_files': result.copied_files,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
