# Provider History / Cooldown Guard v1

## 新增能力
- pair-level cooldown policy
- anomaly / provider gate 触发 cooldown
- cooldown state 持久化
- decision history snapshot

## 配置文件
- `user_data/config/cooldown_policy.json`

## 输出文件
- `agent_service/reports/cooldown_policy_report.json`
- `agent_service/reports/cooldown_state.json`
- `agent_service/reports/decision_history.jsonl`

## 当前示例
- `BTC/USDT`: blocking anomaly 后 cooldown 更长
- `SOL/USDT`: cooldown 期间进一步压低 stake cap
