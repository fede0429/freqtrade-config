# Step 9.3 - Preflight startup chain

This step makes preflight a hard gate in the trader startup path.

## What changed

- Added `services/execution/startup_gate.py` to turn a release profile into:
  - a fresh preflight report
  - a startup bundle artifact
  - a docker compose command preview
- Added `scripts/deploy/start_trader.py`
- Added operator wrappers:
  - `scripts/deploy/start_spot_paper.sh`
  - `scripts/deploy/start_spot_prod.sh`
  - `scripts/deploy/start_futures_paper.sh`

## Operator flow

1. Pick the release profile.
2. Run `start_trader.py`.
3. The script always regenerates preflight first.
4. If checks fail, startup stays `blocked` and docker is not called.
5. If checks pass, startup becomes `armed` and the docker command preview is emitted.
6. Add `--execute` only when you are ready to actually start the service.

## Output artifacts

- `reports/deploy/preflight_<market>_<env>.json`
- `release/runtime/startup_bundle_<market>_<env>.json`

## Why this matters

The trader can no longer be started through the intended path without a current preflight artifact.
The startup bundle also gives you an auditable record of which runtime files were about to be used.
