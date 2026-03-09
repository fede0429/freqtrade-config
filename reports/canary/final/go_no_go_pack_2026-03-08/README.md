# Final Canary Go / No-Go Pack - 2026-03-08

- Built at: 2026-03-08T22:39:03.529816+00:00
- Program overall status: blocked
- Final decision: no_go
- Decision reason: rollback_required_before_canary

## Key Signals
- canary_readiness_status: blocked
- canary_budget_status: blocked
- rollback_status: required
- days_completed: 1
- missing_days: [2, 3, 4, 5, 6, 7]
- scorecard_score: 2/5
- budget_checks: 3/8

## Required Actions
- [ ] fill missing paper-run evidence days before canary promotion
- [ ] complete at least 7 archived paper-run days
- [ ] switch scanner to live mode for the full paper-run window before canary promotion
- [ ] promote to canary only after canary readiness scorecard reaches ready
- [ ] launch canary only through a canary release profile and startup bundle
- [ ] reduce open positions to the canary budget limit
- [ ] cut notional exposure to the canary budget cap
- [ ] resolve drawdown breach before canary launch
- [ ] freeze canary promotion until all failed checks are cleared
- [ ] retain this rollback pack with the corresponding canary readiness pack for audit

## Included Files
- program_status: reports/canary/final/go_no_go_pack_2026-03-08/program_status_2026-03-08.json
- readiness_manifest: reports/canary/final/go_no_go_pack_2026-03-08/canary_readiness_manifest.json
- budget_guard: reports/canary/final/go_no_go_pack_2026-03-08/canary_budget_guard_2026-03-08.json
- rollback_manifest: reports/canary/final/go_no_go_pack_2026-03-08/rollback_manifest.json
- continuity: reports/canary/final/go_no_go_pack_2026-03-08/paper_run_continuity_2026-03-08.json
- scorecard: reports/canary/final/go_no_go_pack_2026-03-08/canary_promotion_scorecard_2026-03-08.json
