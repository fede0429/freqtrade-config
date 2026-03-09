# 7-Day Paper Run Checklist - 2026-03-08

- Overall status: in_progress
- Goal: complete 7 consecutive paper-trading days before canary promotion

## Entry Criteria
- release gate approved for paper
- startup chain is armed
- reporting input type is sqlite
- scanner output produces at least 2 tradable pairs

## Current Observations
- scanner_source_mode: fixture
- pnl_input_type: sqlite
- startup_mode: armed

## Daily Checkpoints
### Day 1 - baseline health
- [ ] archive scanner report
- [ ] archive daily report
- [ ] archive preflight/startup bundle
- [ ] confirm guard_status is healthy

### Day 2 - signal stability
- [ ] compare tradable_pairs with day 1
- [ ] review scanner risk flags drift
- [ ] note any manual overrides

### Day 3 - strategy consistency
- [ ] review active strategy exposures
- [ ] check unexpected candidate activity
- [ ] confirm no blocked strategy receives budget

### Day 4 - drawdown control
- [ ] track current_drawdown_ratio
- [ ] confirm no release gate regressions
- [ ] review losing trades for repeated patterns

### Day 5 - ops discipline
- [ ] verify every startup went through startup_gate
- [ ] ensure evidence bundle is complete
- [ ] refresh program status

### Day 6 - promotion readiness
- [ ] compare realized pnl by strategy
- [ ] review scanner source health
- [ ] prepare canary scorecard notes

### Day 7 - go or hold decision
- [ ] summarize 7-day pnl
- [ ] summarize risk events
- [ ] decide promote/hold/downgrade and record rationale

## Exit Criteria
- 7 consecutive days completed with archived evidence
- no blocked startup days
- risk guard remained healthy or every exception has documented remediation
- owner decision recorded for canary promotion or hold
