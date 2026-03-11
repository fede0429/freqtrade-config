# ROI ROLLOUT V7

新增日志：
- `roi_shadow_trace.jsonl`
- `roi_skip_trace.jsonl`
- `roi_apply_trace.jsonl`

重点检查：
- trade_duration 不足时是否跳过
- 缺失 target_rr 是否跳过
- roi_apply 是否只在 live 打开后生效
