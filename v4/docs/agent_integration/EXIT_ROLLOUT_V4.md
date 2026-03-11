# EXIT ROLLOUT V4

v4 只新增 exit 第一版。

重点检查：
- `exit_shadow_trace.jsonl`
- `exit_skip_trace.jsonl`
- `exit_apply_trace.jsonl`

建议：
- 先 dry-run
- 先验证 agent 的退出理由是否合理
- 不要同时放开 stoploss
