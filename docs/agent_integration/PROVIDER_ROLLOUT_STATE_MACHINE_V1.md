# Provider Rollout State Machine v1

## 新增能力
- pair-level rollout state machine
- trading_mode -> rollout_state 标准映射
- rollout freeze / promote / demote 建议
- rollout state report

## 配置文件
- `user_data/config/rollout_state_policy.json`

## 输出文件
- `agent_service/reports/rollout_state_policy_report.json`
- `agent_service/reports/rollout_state_report.json`

## 当前示例
- `shadow_only` -> `shadow`
- `candidate_shadow` -> `candidate`
- `paper_candidate` -> `paper`
- blocking anomaly / active cooldown 可触发 freeze
