# Step 9.8 - Canary budget guard and rollback pack

This step adds two operator controls before real canary deployment:

1. A canary budget guard that checks readiness, exposure, drawdown, daily loss, and release-channel discipline.
2. A rollback pack builder that collects the current rollback evidence bundle when canary is blocked or needs to be downgraded.

## New files
- `config/canary/runtime/spot.canary.json`
- `services/control/canary_budget_guard.py`
- `services/control/rollback_pack.py`
- `scripts/validate/validate_canary_budget_guard.py`
- `scripts/ops/build_rollback_pack.py`

## Operator flow
1. Generate or refresh the canary readiness pack.
2. Run the canary budget guard.
3. If the guard is blocked, build a rollback pack and stop promotion.
4. Review failed checks and required actions before trying again.
