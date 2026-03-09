# Studio Trading System - Master Runbook

## Daily owner workflow
1. Review the latest scanner output.
2. Review the daily operations report.
3. Check risk guard health.
4. Confirm whether the current environment is paper, canary, or prod.
5. Review any required actions from preflight or risk events.

## Weekly owner workflow
1. Validate strategy stage assignments.
2. Confirm candidate strategies still have zero production budget.
3. Review canary performance versus baseline strategy.
4. Decide whether any strategy should be promoted, held, or downgraded.
5. Archive the weekly status pack.

## Release decision order
1. Configuration valid
2. Risk profile valid
3. Scanner healthy
4. Reporting healthy
5. Strategy registry healthy
6. Preflight approved
7. Checklist signed
8. Release allowed

## Operational truth sources
- `config/runtime/*.json` -> trading runtime truth
- `config/risk/runtime/*.json` -> risk truth
- `strategies/registry/deployment_manifest.json` -> strategy deployment truth
- `reports/scanner/latest_scan.json` -> market entry truth
- `reports/operations/daily/*.json` -> operating truth
- `reports/deploy/preflight_*.json` -> release truth
