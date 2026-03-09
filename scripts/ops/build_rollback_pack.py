from __future__ import annotations

import argparse

from services.control.rollback_pack import build_rollback_pack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--budget-guard', required=True)
    parser.add_argument('--readiness-manifest', required=True)
    parser.add_argument('--program-status', required=True)
    parser.add_argument('--startup-bundle', required=True)
    parser.add_argument('--preflight', required=True)
    parser.add_argument('--daily-report', required=True)
    args = parser.parse_args()

    result = build_rollback_pack(
        output_root=args.output_root,
        as_of=args.as_of,
        budget_guard_path=args.budget_guard,
        readiness_manifest_path=args.readiness_manifest,
        program_status_path=args.program_status,
        startup_bundle_path=args.startup_bundle,
        preflight_path=args.preflight,
        daily_report_path=args.daily_report,
    )
    print(result.manifest_path)
    print(result.summary_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
