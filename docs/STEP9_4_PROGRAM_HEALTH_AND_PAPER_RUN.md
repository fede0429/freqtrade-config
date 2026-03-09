# STEP 9.4 - Program Health Rollup and 7-Day Paper Run Checklist

## Goal
Promote the project from one-off integration work to continuous operating validation.

## What changed
- Expand `program_status` so it includes release gate, market intelligence, operations reporting, startup chain, and paper-run validation milestones.
- Add milestone details such as scanner source mode, reporting input type, startup mode, and current paper-run completion state.
- Render both JSON and Markdown program status outputs.
- Add a dedicated generator for a 7-day paper-run checklist.

## Why this matters
The project now has a visible daily control layer:
- one file to answer whether the system is blocked, in progress, or ready
- one checklist to drive the first 7 consecutive paper-trading days

## Operating interpretation
- `market_intelligence = in_progress` means scanner is producing usable outputs, but the source is not yet live.
- `operations_reporting = ready` means daily reporting is already backed by sqlite inputs.
- `startup_chain = ready` means the only approved launch path is now armed through `start_trader.py`.
- `paper_run_validation = in_progress` means the system is now ready to begin accumulating day-by-day evidence.

## Commands
Render updated program status:

```bash
PYTHONPATH=. python3 scripts/ops/render_program_status.py \
  --preflight reports/deploy/preflight_spot_paper.json \
  --report reports/operations/daily/studio_daily_report_2026-03-08.json \
  --scanner reports/scanner/latest_scan_step9.json \
  --startup-bundle release/runtime/startup_bundle_spot_paper.json \
  --output reports/roadmap/program_status_2026-03-08.json \
  --markdown-output reports/roadmap/program_status_2026-03-08.md
```

Generate the 7-day paper checklist:

```bash
PYTHONPATH=. python3 scripts/ops/generate_paper_run_checklist.py \
  --program-status reports/roadmap/program_status_2026-03-08.json \
  --output-json reports/roadmap/paper_run_checklist_2026-03-08.json \
  --output-md reports/roadmap/paper_run_checklist_2026-03-08.md
```
