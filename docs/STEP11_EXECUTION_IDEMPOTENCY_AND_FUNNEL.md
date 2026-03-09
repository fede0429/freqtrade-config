# Step 11 - Execution Connector, Idempotency, Missed Alpha, Funnel

This step adds a production-oriented bridge between meta decisions and a real execution endpoint.

## Added
- `apps/execution/dispatch_meta_decisions.py`
- `services/execution/real_connector.py`
- `services/execution/idempotency.py`
- `services/analytics/signal_pipeline_loader.py`

## What changed
- Accepted and reduced decisions can now be dispatched to a connector.
- Connector mode supports:
  - `dry_run`
  - `webhook` for a live HTTP execution adapter
- Every dispatch is written into `execution_dispatch_log`.
- `decision_id + request_hash` is used as the idempotency boundary.
- Daily report can now include:
  - execution funnel
  - missed alpha stats from rejected/delayed shadow outcomes

## Notes
- This step does not place exchange orders by itself.
- The live path is intentionally behind an explicit webhook profile.
- Repeated dispatch calls with the same decision payload are deduplicated.
