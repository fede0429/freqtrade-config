# Program Status - 2026-03-08

- Overall status: blocked

## Milestones
### release_gate
- Status: ready
- approved: True
- mode: release
- startup_mode: armed
- Evidence: reports/deploy/preflight_spot_paper.json, release/runtime/startup_bundle_spot_paper.json
- Next actions:
  - Re-render config, risk, scanner, reporting, and strategy manifests before startup.
  - Capture preflight artifact and attach it to the operating log.

### market_intelligence
- Status: in_progress
- source_mode: fixture
- selected_count: 3
- candidate_count: 6
- market_regime: trend
- Evidence: reports/scanner/latest_scan.json
- Next actions:
  - switch scanner source from fixture to live exchange data

### operations_reporting
- Status: ready
- pnl_input_type: sqlite
- closed_trades: 6
- open_positions: 3
- Evidence: reports/operations/daily/studio_daily_report_2026-03-08.json
- Next actions:
  - continue daily report automation

### startup_chain
- Status: ready
- startup_mode: armed
- service_name: freqtrade-spot
- release_channel: paper
- Evidence: release/runtime/startup_bundle_spot_paper.json
- Next actions:
  - Review preflight report before starting trader.
  - Do not bypass blocked startup without explicitly fixing failed checks.

### paper_run_validation
- Status: in_progress
- guard_status: healthy
- tradable_pairs: 3
- preflight_approved: True
- days_completed: 1
- days_required: 7
- evidence_root: reports/evidence/paper_run
- continuity_missing_days: [2, 3, 4, 5, 6, 7]
- scorecard_status: blocked
- scorecard_score: 2/5
- continuity_ok: False
- Evidence: reports/evidence/paper_run/day-01/evidence_manifest.json, reports/roadmap/paper_run_continuity_2026-03-08.json, reports/roadmap/canary_promotion_scorecard_2026-03-08.json
- Next actions:
  - run 7 consecutive paper days and archive scanner, report, and preflight outputs each day
  - confirm guard_status stays healthy throughout the validation window
  - review any strategy with unexplained exposure or repeated losses before canary promotion
  - fill missing evidence days: [2, 3, 4, 5, 6, 7]
  - fill missing paper-run evidence days before canary promotion
  - complete at least 7 archived paper-run days
  - switch scanner to live mode for the full paper-run window before canary promotion
  - continue archiving evidence packs under reports/evidence/paper_run

### canary_readiness
- Status: blocked
- verdict: not_eligible
- score: 2/5
- days_completed: 1
- days_required: 7
- missing_days: [2, 3, 4, 5, 6, 7]
- scanner_not_live_days: [1]
- continuity_ok: False
- Evidence: reports/roadmap/paper_run_continuity_2026-03-08.json, reports/roadmap/canary_promotion_scorecard_2026-03-08.json
- Next actions:
  - fill missing paper-run evidence days before canary promotion
  - complete at least 7 archived paper-run days
  - switch scanner to live mode for the full paper-run window before canary promotion

### canary_budget_guard
- Status: blocked
- verdict: rollback_required_before_canary
- checks_passed: 3/8
- open_positions: 3
- open_exposure_usd: 6750.0
- max_drawdown_ratio: 0.1
- Evidence: reports/canary/readiness/canary_budget_guard_2026-03-08.json
- Next actions:
  - promote to canary only after canary readiness scorecard reaches ready
  - launch canary only through a canary release profile and startup bundle
  - reduce open positions to the canary budget limit
  - cut notional exposure to the canary budget cap
  - resolve drawdown breach before canary launch

### rollback_readiness
- Status: blocked
- rollback_status: required
- rollback_reason: rollback_required_before_canary
- failed_checks: ['canary_readiness_verdict', 'startup_channel_match', 'open_positions_within_limit', 'notional_within_limit', 'drawdown_within_limit']
- Evidence: reports/canary/rollback/rollback_pack_2026-03-08/rollback_manifest.json
- Next actions:
  - promote to canary only after canary readiness scorecard reaches ready
  - launch canary only through a canary release profile and startup bundle
  - reduce open positions to the canary budget limit
  - cut notional exposure to the canary budget cap
  - resolve drawdown breach before canary launch
  - freeze canary promotion until all failed checks are cleared
  - retain this rollback pack with the corresponding canary readiness pack for audit
