# Freqtrade Agent Bridge

This branch wires an external agent sidecar into a Freqtrade strategy with a staged, low-risk rollout.

Current guardrails:
- Default mode is shadow mode.
- Agent callbacks only go live when the overlay enables them.
- Decision cache freshness is enforced in live and dry-run.
- Backtests can bypass cache TTL unless `enforce_cache_ttl_in_backtest` is turned on.
- The hybrid launcher keeps refreshing the decision cache while Freqtrade is running.

Important runtime entrypoints:
- `scripts/run_agent_service.sh`
- `scripts/run_hybrid_stack.sh`
- `user_data/strategies/AgentBridgeStrategy.py`
- `user_data/config/agent_overlay.json`
