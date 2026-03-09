# Step 1 - Repository Restructure

This workspace is the phase-1 migration output.

## Objectives completed
- Separated production, candidate, experimental, and archive strategies.
- Moved active scanner and reporter into app-style entrypoints.
- Isolated legacy configs away from production config paths.
- Preserved original README and docker-compose as references.

## Proposed next tasks
1. Build config layering: common + spot/futures + paper/prod overrides.
2. Create validation scripts for config and strategy smoke tests.
3. Add risk service module before modifying strategy logic.
