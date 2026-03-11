# ROI ROLLOUT V7

New traces:
- `roi_shadow_trace.jsonl`
- `roi_skip_trace.jsonl`
- `roi_apply_trace.jsonl`

Checks:
- `use_custom_roi` must be enabled in the strategy.
- `trade_duration` must pass the configured minimum.
- `target_profit_ratio` can be used directly.
- `target_rr` must be converted with a stop reference before it becomes a Freqtrade ROI value.
- Parent strategy ROI should be preserved when the bridge is disabled or skipped.
- ROI should apply only after the callback is enabled outside shadow mode.
