# STEP 10: Live scanner rollout

## Goal
Switch the scanner from fixture mode to live market data in a controlled way, without skipping release governance.

## What changed
- Added `services/scanner/live_health.py` to validate live-source prerequisites.
- Added `scripts/bootstrap/render_live_scanner_profile.py` to derive a live scanner runtime profile.
- Added `scripts/validate/validate_live_scanner_cutover.py` for pre-cutover validation.
- Added `scripts/ops/build_live_scanner_cutover_pack.py` to bundle the cutover evidence.

## Recommended order
1. Render a live scanner runtime profile from the current paper profile.
2. Validate the profile offline.
3. On the deployment host, run the same validator with `--probe-live`.
4. Run one controlled live scanner cycle.
5. Archive the first live scan into the day evidence pack.
6. Re-run steps 9.6 to 9.9.

## Commands
```bash
PYTHONPATH=. python3 scripts/bootstrap/render_live_scanner_profile.py \
  config/scanner/runtime/spot.paper.json \
  config/scanner/runtime/spot.paper.live.json

PYTHONPATH=. python3 scripts/validate/validate_live_scanner_cutover.py \
  --profile config/scanner/runtime/spot.paper.live.json \
  --output-json reports/scanner/live_cutover_validation_2026-03-08.json \
  --output-md reports/scanner/live_cutover_validation_2026-03-08.md
```

On the real deployment host:
```bash
PYTHONPATH=. python3 scripts/validate/validate_live_scanner_cutover.py \
  --profile config/scanner/runtime/spot.paper.live.json \
  --probe-live \
  --output-json reports/scanner/live_cutover_validation_host.json \
  --output-md reports/scanner/live_cutover_validation_host.md
```

## Honest status
This step prepares the live scanner cutover and validates it offline. It does not claim that a live exchange probe has succeeded in the current environment.
