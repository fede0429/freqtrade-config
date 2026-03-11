# Shadow Audit Schema

本版新增 shadow / live 对账日志文件：

- `stake_decision_trace.jsonl`
- `stake_apply_trace.jsonl`
- `exit_shadow_trace.jsonl`
- `stoploss_shadow_trace.jsonl`
- `roi_shadow_trace.jsonl`
- `entry_confirm_trace.jsonl`

## stake_decision_trace
记录：
- pair
- mode
- proposed_stake
- decision

## stake_apply_trace
记录：
- pair
- applied
- confidence
- multiplier
- final_stake
