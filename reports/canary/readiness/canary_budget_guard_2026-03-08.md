# Canary Budget Guard

- Status: blocked
- Verdict: rollback_required_before_canary
- Checks passed: 3/8

## Failed Checks
- canary_readiness_verdict: {'status': 'blocked', 'verdict': 'not_eligible', 'score': '2/5'}
- startup_channel_match: {'startup_release_channel': 'paper', 'allowed_release_channel': 'canary'}
- open_positions_within_limit: {'open_positions': 3, 'limit': 2}
- notional_within_limit: {'open_exposure_usd': 6750.0, 'limit_usd': 1500}
- drawdown_within_limit: {'max_drawdown_ratio': 0.1, 'limit_ratio': 0.03}

## Required Actions
- [ ] promote to canary only after canary readiness scorecard reaches ready
- [ ] launch canary only through a canary release profile and startup bundle
- [ ] reduce open positions to the canary budget limit
- [ ] cut notional exposure to the canary budget cap
- [ ] resolve drawdown breach before canary launch
