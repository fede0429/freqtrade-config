# Step 6 - Reporting and Operations Dashboard

This step upgrades reporting from a post-trade script into a daily operating layer.

## Goals
- Merge scanner, risk, strategy deployment, and PnL into one daily report
- Produce both JSON and Markdown outputs
- Create a stable interface for future Telegram/email/report pipelines

## New Components
- `config/reporting/...`: reporting profiles and environment-specific paths
- `services/analytics/...`: operations report builder and renderers
- `apps/reporter/performance_report.py`: daily report entrypoint
- `reports/operations/daily/...`: generated report artifacts

## Daily Report Contents
- Executive summary with net PnL and trade count
- Scanner regime, selected tradable pairs, and market flags
- Risk guard state and drawdown snapshot
- Strategy health by lifecycle stage
- Top winners and losers
- Risk event log and narrative commentary

## Next Integration Targets
- Feed real trade database metrics instead of mock inputs
- Send report summaries to Telegram/Slack
- Add weekly rollup and strategy attribution charts
