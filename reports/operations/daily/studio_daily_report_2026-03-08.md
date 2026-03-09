# Studio Daily Operations Report - 2026-03-08

## Executive Summary
- Market: spot
- Profile: paper
- Net PnL: 207.50 USD (0.83%)
- Realized / Unrealized: 167.50 / 69.00 USD
- Fees: 29.00 USD
- Open positions: 3
- Closed trades: 6

## Data Sources
- PnL input type: sqlite
- Scanner input type: fixture

## Market & Scanner
- Regime: trend
- Market pressure: allow
- Tradable pairs: SOL/USDT, ETH/USDT, BTC/USDT
- Scanner risk flags: deep_drawdown, low_liquidity

## Risk Status
- Guard status: healthy
- Current drawdown: 0.0018
- Max drawdown threshold: 0.1000
- Scanner approval required: True

## Strategy Health
- AdaptiveMetaStrategy: stage=canary, status=active, exposure=2100.00 USD, realized_pnl=13.00 USD
- UniversalMACD_V2: stage=production, status=active, exposure=4650.00 USD, realized_pnl=154.50 USD
- UniversalMACD_Futures: stage=dry_run, status=idle, exposure=0.00 USD, realized_pnl=0.00 USD
- TrendEMAStrategy: stage=candidate, status=idle, exposure=0.00 USD, realized_pnl=0.00 USD

## Top Winners
- BTC/USDT / UniversalMACD_V2: 91.00 USD
- ETH/USDT / AdaptiveMetaStrategy: 54.00 USD
- AVAX/USDT / UniversalMACD_V2: 41.00 USD

## Top Losers
- DOGE/USDT / AdaptiveMetaStrategy: -23.00 USD
- XRP/USDT / AdaptiveMetaStrategy: -18.00 USD

## Execution Funnel
- Signals: 4
- Accept/Reduce: 2
- Delay/Reject: 2
- Dispatched: 2
- Accepted: 2
- Partial: 0
- Filled: 2
- Failed: 0
- Cancelled: 0
- Deduplicated: 2

## Decision to Fill
- Fill rate vs dispatched: 1.0000
- Avg slippage: 6.0000 bps
- Total execution fees: 65.23912000
- Avg fill latency: 8.5480 s

## Outcome Comparison
- Accepted decisions: 2
- Accepted filled orders: 2
- Accepted reconciled trades: 0
- Accepted trade pnl: 0.0000 USD
- Accepted trade avg ratio: 0.0000
- Rejected shadow count: 2
- Rejected shadow avg ratio: 0.0120
- Actual vs rejected shadow ratio gap: -0.0120

## Integrity Checks
- Duplicate dispatches: 0
- Orphan orders: 0
- Filled unreconciled orders: 2
- State anomaly count: 0

## Traceability
- Orders: 0
- Traced orders: 0
- Trace coverage ratio: 0.0000
- Distinct runs: 0
- Distinct traces: 0

## Missed Alpha
- Rejected/Delayed shadows tracked: 2
- Profitable rejected shadows: 1
- Profitable ratio: 0.5000
- Best rejected pnl ratio: 0.0360

## Risk Events
- [medium] scanner_flag: Market flagged high_volatility but entries remained allowed for top-ranked symbols.
- [low] drawdown_watch: Intra-day drawdown remained below guard threshold.

## Replace Cost Analysis
- Replace orders: 0
- Avg replace slippage: 0.0000 bps
- Total replace fees: 0.00000000
- Avg replace price move: 0.0000 bps

## Strategy-level Missed Alpha
- TrendEMAStrategy: rejected=1, profitable=1, avg_ratio=0.0360, best_ratio=0.0360
- AdaptiveMetaStrategy: rejected=1, profitable=0, avg_ratio=-0.0120, best_ratio=-0.0120

## Narrative
- Net daily result was 207.50 USD (0.83%) across 6 closed trades.
- Scanner classified the market as trend and approved 3 tradable pairs.
- Market-level warnings: deep_drawdown, low_liquidity.
- Best contributing active strategy was UniversalMACD_V2 at 154.50 USD realized PnL.
- Risk guard status remained healthy with current drawdown 0.0018.
- Scanner is not live yet; current source mode is fixture.
- Execution funnel: 4 signals -> 2 accepted/reduced -> 2 dispatched -> 2 filled.
- Decision-to-fill quality: fill_rate=100.00%, avg_slippage=6.00 bps, fees=65.2391.
- Missed alpha watch: 1 profitable rejected/delayed shadows out of 2 tracked.
- Outcome comparison: accepted real trades avg_ratio=0.0000, rejected shadow avg_ratio=0.0120, gap=-0.0120, strong_recon=0.
- Replace cost: 0 replace orders, avg_slippage=0.00 bps, fees=0.0000.
- Integrity: duplicate_dispatches=0, filled_unreconciled=2, state_anomalies=0.
- Traceability: coverage=0.00%, runs=0, traces=0.
- PnL input source was sqlite.
- SQLite input freqtrade_tradesv3_sample.sqlite exists=True fixture=True updated=2026-03-09T17:46:50.114070Z.
- Scanner input source was fixture.
