# Daily Close Health Pack

- As of date: all
- Overall status: attention
- Stability score: 80

## Top Alerts
- [HIGH] filled_unreconciled_orders: 2 filled orders have no reconciliation row

## Recommended Actions
- filled_unreconciled_orders: 2 filled orders have no reconciliation row Run `scripts/ops/auto_repair_signal_pipeline.py --fix unreconciled --profile <execution_profile>`.

## Replay Entry Points
- `python apps/execution/replay_execution_trace.py --execution-db reports/execution/dispatch_state.sqlite --signal-pipeline-db reports/execution/dispatch_state.sqlite --order-id exec:dec-001`
- `python apps/execution/replay_execution_trace.py --execution-db reports/execution/dispatch_state.sqlite --signal-pipeline-db reports/execution/dispatch_state.sqlite --decision-id dec-001`
- `python apps/execution/replay_execution_trace.py --execution-db reports/execution/dispatch_state.sqlite --signal-pipeline-db reports/execution/dispatch_state.sqlite --signal-id sig-001`
