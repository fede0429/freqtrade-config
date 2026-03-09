# STEP 9.5 - paper run evidence packs

This step turns the 7-day paper-run checklist into an auditable archive process.

## What changed

- Added `services/control/evidence_pack.py` to create one evidence pack per paper day.
- Added `scripts/ops/archive_paper_run_evidence.py` to archive scanner, report, preflight, startup bundle, and program status into `reports/evidence/paper_run/day-XX/`.
- Extended `services/control/program_state.py` so `paper_run_validation` now counts archived days automatically.
- Extended `scripts/ops/render_program_status.py` with `--evidence-root` so the status report can show `days_completed`.

## Evidence pack contents

Each day archive includes:

- `program_status_*.json`
- scanner report
- daily operations report
- preflight report
- startup bundle
- `evidence_manifest.json`
- `README.md`

## Typical usage

Archive the current paper day:

```bash
PYTHONPATH=. python3 scripts/ops/archive_paper_run_evidence.py \
  --program-status reports/roadmap/program_status_2026-03-08.json \
  --scanner reports/scanner/latest_scan.json \
  --report reports/operations/daily/studio_daily_report_2026-03-08.json \
  --preflight reports/deploy/preflight_spot_paper.json \
  --startup-bundle release/runtime/startup_bundle_spot_paper.json \
  --evidence-root reports/evidence/paper_run
```

Refresh program status with archived day counting:

```bash
PYTHONPATH=. python3 scripts/ops/render_program_status.py \
  --preflight reports/deploy/preflight_spot_paper.json \
  --report reports/operations/daily/studio_daily_report_2026-03-08.json \
  --scanner reports/scanner/latest_scan.json \
  --startup-bundle release/runtime/startup_bundle_spot_paper.json \
  --evidence-root reports/evidence/paper_run \
  --output reports/roadmap/program_status_2026-03-08.json \
  --markdown-output reports/roadmap/program_status_2026-03-08.md
```

## Expected operating discipline

- Archive one evidence pack for every paper-trading day.
- Do not skip days or overwrite old day folders.
- Use the `README.md` inside each day folder for quick operator notes.
- Only consider canary promotion after 7 complete day folders exist and the guard stayed healthy.
