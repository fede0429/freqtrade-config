# Step 9.9 - Budget and rollback backfeed with final go/no-go pack

This step closes the operator loop before any canary release decision.

## What changed
- `program_status` now accepts:
  - `--budget-guard`
  - `--rollback-manifest`
- Two new milestones are visible at the top level:
  - `canary_budget_guard`
  - `rollback_readiness`
- A final `go / no-go` pack is generated from:
  - program status
  - canary readiness manifest
  - budget guard
  - rollback manifest
  - continuity
  - scorecard

## Operator meaning
The go/no-go pack is the last decision artifact before a canary launch. If the decision remains `no_go`, you should not continue to a real canary release.
