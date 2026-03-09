# Canary Rollback Pack - 2026-03-08

- Built at: 2026-03-08T22:33:00.416439+00:00
- Rollback status: required
- Reason: rollback_required_before_canary

## Trigger Summary
- budget_guard_status: blocked
- failed_checks: ['canary_readiness_verdict', 'startup_channel_match', 'open_positions_within_limit', 'notional_within_limit', 'drawdown_within_limit']
- startup_mode: armed
- preflight_approved: True
- program_overall_status: blocked
- daily_guard_status: healthy

## Required Actions
- [ ] promote to canary only after canary readiness scorecard reaches ready
- [ ] launch canary only through a canary release profile and startup bundle
- [ ] reduce open positions to the canary budget limit
- [ ] cut notional exposure to the canary budget cap
- [ ] resolve drawdown breach before canary launch
- [ ] freeze canary promotion until all failed checks are cleared
- [ ] retain this rollback pack with the corresponding canary readiness pack for audit

## Included Files
- budget_guard: reports/canary/rollback/rollback_pack_2026-03-08/canary_budget_guard_2026-03-08.json
- readiness_manifest: reports/canary/rollback/rollback_pack_2026-03-08/canary_readiness_manifest.json
- program_status: reports/canary/rollback/rollback_pack_2026-03-08/program_status_2026-03-08.json
- startup_bundle: reports/canary/rollback/rollback_pack_2026-03-08/startup_bundle_spot_paper.json
- preflight_report: reports/canary/rollback/rollback_pack_2026-03-08/preflight_spot_paper.json
- daily_report: reports/canary/rollback/rollback_pack_2026-03-08/studio_daily_report_2026-03-08.json
