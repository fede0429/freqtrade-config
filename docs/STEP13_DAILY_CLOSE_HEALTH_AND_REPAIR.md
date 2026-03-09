# STEP13 Daily Close Health and Repair

This step adds three production-facing capabilities:

1. Graded incident handling for pipeline alerts
2. Auto-repair entrypoints for common integrity issues
3. A single daily close health pack with replay commands

## New commands

```bash
python scripts/ops/render_signal_pipeline_alerts.py \
  --signal-pipeline-db reports/execution/dispatch_state.sqlite \
  --execution-db reports/execution/dispatch_state.sqlite \
  --output-json reports/observability/signal_pipeline_alerts.json \
  --output-md reports/observability/signal_pipeline_alerts.md
```

```bash
python scripts/ops/auto_repair_signal_pipeline.py \
  --signal-pipeline-db reports/execution/dispatch_state.sqlite \
  --execution-db reports/execution/dispatch_state.sqlite \
  --profile config/execution/runtime/spot.paper.file_status.json \
  --fix trace --fix unreconciled --apply
```

```bash
python scripts/ops/build_daily_close_health_pack.py \
  --signal-pipeline-db reports/execution/dispatch_state.sqlite \
  --execution-db reports/execution/dispatch_state.sqlite \
  --output-json reports/observability/daily_close_health_pack.json \
  --output-md reports/observability/daily_close_health_pack.md
```

## Outcome

By the end of this step, the system can:

- tell ops who owns an incident and what to do next
- auto-repair trace gaps and retry unreconciled fills when trade data is available
- produce a single end-of-day pack that combines alerts, stability, and replay entry points
