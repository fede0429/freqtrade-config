# STEP 8 - Long-term Upgrade Path and Final Program Closure

## Goal
Turn the rebuilt trading repository into a studio operating system with a clear 12-week path from paper readiness to disciplined production rollout.

## What this step adds
1. A 12-week upgrade plan.
2. A master operating model for paper -> canary -> prod.
3. A program status renderer that summarizes whether the studio is ready, blocked, or still in progress.
4. A single runbook that tells the owner what to review each day and each week.

## Promotion ladder
- **paper**: prove operational stability
- **canary**: prove controlled real-money behavior with capped budget
- **prod**: release only after gates, reports, scanner, and risk all align

## Required weekly rituals
- Monday: review scanner regime behavior and pair approvals
- Wednesday: review strategy health and any risk events
- Friday: review promotion readiness and release checklist
- Sunday: publish weekly scorecard and next-week decisions

## Exit criteria for the whole program
- Scanner is using live market data reliably
- Daily reporting is sourced from real trade data
- Preflight is mandatory before paper and prod release
- Canary allocation is isolated and auditable
- Production release has a signed checklist and rollback plan
