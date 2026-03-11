# Agent Bridge README

This integration keeps the base Freqtrade strategy in control and lets the agent layer add gated adjustments.

## Runtime model
- `AgentBridgeStrategy` inherits the base trading strategy.
- The agent writes signals to `agent_service/reports/latest_agent_signals.json`.
- `scripts/run_agent_service.sh` converts that payload into `user_data/agent_runtime/state/decision_cache.json`.
- `scripts/run_hybrid_stack.sh` refreshes the cache continuously and then launches Freqtrade.

## Callback behavior
- Stake: can scale the proposed stake after confidence and governance checks.
- Exit: can add an exit reason, but falls back to the base strategy when no agent action is applied.
- Stoploss: can only tighten risk and never removes the base strategy stoploss behavior.
- ROI: is enabled explicitly and derives a profit ratio from either `target_profit_ratio` or `target_rr * abs(agent_stoploss)`.
- Entry confirm: can block entries only after confidence, governance, pair allowlist, and freshness checks pass.

## Launch example
```bash
scripts/run_hybrid_stack.sh freqtrade trade --config user_data/config.json --strategy AgentBridgeStrategy
```
