# Step 9.7 - Continuity Backfeed and Canary Readiness Pack

This step closes the loop between paper-run evidence, continuity validation, canary scorecard, and program status.

## What changed
- `program_status` now accepts continuity and scorecard inputs.
- A dedicated `canary_readiness` milestone is rendered in the top-level program state.
- `paper_run_validation` now includes continuity and scorecard details.
- A new canary readiness pack bundles the latest program status, continuity report, scorecard, checklist, startup bundle, preflight report, and all archived evidence manifests.

## Why this matters
The operator should not need to manually compare multiple JSON files to determine if the system is eligible for canary promotion. The program status should directly reflect promotion readiness, and a single readiness pack should exist for audit and review.

## New commands
Render program status with promotion evidence:

```bash
PYTHONPATH=. python3 scripts/ops/render_program_status.py \
  --preflight reports/deploy/preflight_spot_paper.json \
  --report reports/operations/daily/studio_daily_report_2026-03-08.json \
  --scanner reports/scanner/latest_scan.json \
  --startup-bundle release/runtime/startup_bundle_spot_paper.json \
  --evidence-root reports/evidence/paper_run \
  --continuity reports/roadmap/paper_run_continuity_2026-03-08.json \
  --scorecard reports/roadmap/canary_promotion_scorecard_2026-03-08.json \
  --output reports/roadmap/program_status_2026-03-08.json \
  --markdown-output reports/roadmap/program_status_2026-03-08.md
```

Build canary readiness pack:

```bash
PYTHONPATH=. python3 scripts/ops/build_canary_readiness_pack.py \
  --as-of 2026-03-08 \
  --program-status reports/roadmap/program_status_2026-03-08.json \
  --continuity reports/roadmap/paper_run_continuity_2026-03-08.json \
  --scorecard reports/roadmap/canary_promotion_scorecard_2026-03-08.json \
  --evidence-root reports/evidence/paper_run \
  --paper-run-checklist reports/roadmap/paper_run_checklist_2026-03-08.json \
  --startup-bundle release/runtime/startup_bundle_spot_paper.json \
  --preflight reports/deploy/preflight_spot_paper.json \
  --output-root reports/canary/readiness
```

## Current expectation
With only one archived paper day and scanner still in fixture mode, `canary_readiness` should remain blocked. This is the desired result until the paper window and live scanner requirement are both satisfied.
