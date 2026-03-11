# Decision Cache Schema

```json
{
  "ts": "ISO8601",
  "source": "agent_service_v24",
  "pairs": {
    "BTC/USDT": {
      "agent_enabled": true,
      "confidence": 0.78,
      "stake_multiplier": 1.35,
      "entry_allowed": true,
      "exit_signal": false,
      "exit_reason": null,
      "stoploss_mode": "tighten_only",
      "agent_stoploss": -0.04,
      "target_rr": 2.8,
      "target_profit_ratio": null,
      "governance_gate": "passed"
    }
  }
}
```

Notes:
- `ts` should represent when the agent payload was produced.
- `target_profit_ratio` is a direct ROI target such as `0.08`.
- `target_rr` is a risk-reward multiple. When used, the strategy converts it to ROI with `abs(agent_stoploss) * target_rr`.
- Live callbacks are ignored when the cache is stale, the pair is not allowed, or governance is blocked.
