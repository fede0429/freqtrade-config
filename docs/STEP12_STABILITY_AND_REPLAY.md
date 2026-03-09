# STEP12 - Stability and Replay

This step adds five production-hardening pieces:

1. End-to-end `run_id` / `trace_id` propagation for execution dispatch, status sync, replace, and reconciliation.
2. Execution-order transition logging and stricter status-transition validation.
3. Stability assessment script for duplicate dispatches, orphan orders, unreconciled fills, anomalies, and trace coverage.
4. Meta-decision evaluation script for quick threshold/outcome inspection.
5. Single-chain replay entrypoint to inspect signal -> decision -> dispatch -> execution -> reconciliation.
