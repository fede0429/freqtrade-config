from __future__ import annotations

import argparse

from services.control.go_no_go_pack import build_go_no_go_pack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--program-status', required=True)
    parser.add_argument('--readiness-manifest', required=True)
    parser.add_argument('--budget-guard', required=True)
    parser.add_argument('--rollback-manifest', required=True)
    parser.add_argument('--continuity', required=True)
    parser.add_argument('--scorecard', required=True)
    args = parser.parse_args()

    result = build_go_no_go_pack(
        as_of=args.as_of,
        output_root=args.output_root,
        program_status_path=args.program_status,
        readiness_manifest_path=args.readiness_manifest,
        budget_guard_path=args.budget_guard,
        rollback_manifest_path=args.rollback_manifest,
        continuity_path=args.continuity,
        scorecard_path=args.scorecard,
    )
    print(result.manifest_path)
    print(result.summary_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
