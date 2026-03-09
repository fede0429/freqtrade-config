# Signal Pipeline Incident Summary

- Severity: high
- Alert count: 1
- As of date: all
- Disposition: page-now

## Incidents
- [HIGH] filled_unreconciled_orders: 2 filled orders have no reconciliation row
  - Owner: execution-ops
  - Auto repairable: True
  - Suggested command: `scripts/ops/auto_repair_signal_pipeline.py --fix unreconciled --profile <execution_profile>`
  - Step: Run the auto-repair script with a trades DB or execution profile to retry reconciliation for unreconciled filled orders.
  - Step: If strong-key mapping is missing, verify external_order_id / venue_order_id propagation from the real executor.
  - Step: Replay one affected order to confirm dispatch, fill sync, and reconciliation events line up.

## Next Actions
- filled_unreconciled_orders: 2 filled orders have no reconciliation row Run `scripts/ops/auto_repair_signal_pipeline.py --fix unreconciled --profile <execution_profile>`.
