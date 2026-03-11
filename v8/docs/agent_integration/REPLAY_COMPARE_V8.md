# REPLAY COMPARE V8

v8 新增 dry-run 对账汇总器。

输入：
- `user_data/agent_runtime/audit/*.jsonl`

输出：
- `agent_service/reports/replay_compare_pack.json`

用途：
- 观察每类 callback 的触发次数
- 抽样查看最近几条 apply / skip / shadow 记录
- 为后续做策略行为回放和对账提供入口
