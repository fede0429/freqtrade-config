# STOPLOSS ROLLOUT V5

v5 只新增 stoploss tighten 第一版。

重点检查：
- `stoploss_shadow_trace.jsonl`
- `stoploss_skip_trace.jsonl`
- `stoploss_apply_trace.jsonl`

规则：
- 只接受 `stoploss_mode = tighten_only`
- 缺失 `agent_stoploss` 时绝不应用
- roi 仍保持关闭
