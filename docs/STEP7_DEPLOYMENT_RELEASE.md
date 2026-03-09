# Step 7 - Deployment and Release Governance

This step upgrades the project from manual startup into a controlled release path.

## Goals
- Split release profiles by market and environment
- Add a preflight approval layer before startup
- Generate a repeatable release checklist artifact
- Prepare a stable path from dev to paper to prod

## New Components
- `config/release/...`: release governance profiles
- `services/execution/...`: release planner and decision types
- `scripts/deploy/preflight_check.py`: environment release gate
- `scripts/deploy/generate_release_checklist.py`: operator-facing checklist
- `reports/deploy/...`: preflight artifacts and Markdown release checklist

## Release Flow
1. Render release profile
2. Validate release governance
3. Run preflight check
4. Review generated checklist
5. Start the matching compose entrypoint
6. Attach artifacts to the operating log

## Promotion Policy
- `dev`: fastest iteration path with relaxed gating
- `paper`: full dry-run operating path with required guard health
- `prod`: strict path that blocks candidate and dry-run strategies from receiving live budget

## Next Integration Targets
- Wire the preflight result into the trader entrypoint
- Add canary traffic and rollback commands
- Persist release approvals into an audit timeline
