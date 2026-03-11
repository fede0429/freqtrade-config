# ENTRY CONFIRM ROLLOUT V6

新增日志：
- `entry_confirm_trace.jsonl`
- `entry_confirm_skip_trace.jsonl`
- `entry_confirm_block_trace.jsonl`
- `entry_confirm_apply_trace.jsonl`

重点检查：
- 低置信度时是否正确阻止开仓
- entry_allowed=false 时是否正确拦截
- shadow 模式下是否只记录不拦截
