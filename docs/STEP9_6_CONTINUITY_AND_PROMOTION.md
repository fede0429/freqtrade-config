# Step 9.6 - Continuity Check and Canary Promotion Scorecard

This step adds two operating controls on top of evidence packs:

1. A continuity validator for the 7-day paper run.
2. A canary promotion scorecard.

## What is validated

The continuity validator checks whether archived day packs are contiguous and whether each archived day preserved release discipline:

- evidence days are sequential
- guard status stayed healthy
- startup mode stayed armed
- release remained approved
- scanner ran in live mode when live is required

## Scripts

### Continuity validation

```bash
PYTHONPATH=. python3 scripts/ops/validate_paper_run_continuity.py \
  --evidence-root reports/evidence/paper_run \
  --expected-days 7 \
  --output-json reports/roadmap/paper_run_continuity_2026-03-08.json \
  --output-md reports/roadmap/paper_run_continuity_2026-03-08.md
```

### Canary promotion scorecard

```bash
PYTHONPATH=. python3 scripts/ops/render_canary_promotion_scorecard.py \
  --evidence-root reports/evidence/paper_run \
  --expected-days 7 \
  --output-json reports/roadmap/canary_promotion_scorecard_2026-03-08.json \
  --output-md reports/roadmap/canary_promotion_scorecard_2026-03-08.md
```

## Interpretation

- `ready`: paper run is complete and eligible for canary promotion.
- `in_progress`: some controls are satisfied but the window is incomplete or a non-blocking requirement is still open.
- `blocked`: too many controls failed to consider canary promotion.

Current expected behavior for this project state:

- continuity is incomplete because only Day 1 is archived
- promotion is on hold because 7 days are not complete and scanner is not yet live
