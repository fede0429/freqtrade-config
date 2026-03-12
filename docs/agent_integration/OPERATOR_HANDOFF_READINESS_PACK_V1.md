# Operator Handoff / Final Readiness Pack v1

## 新增能力
- final readiness checklist
- pair-level go / hold / review verdict
- operator handoff pack
- review summary report
- 收口前人工检查入口

## 配置文件
- `user_data/config/readiness_policy.json`

## 输出文件
- `agent_service/reports/readiness_policy_report.json`
- `agent_service/reports/review_summary_report.json`
- `agent_service/reports/operator_handoff_pack.json`

## verdict 含义
- `go`: 可进入下一阶段候选
- `review`: 建议人工复核
- `hold`: 保持当前阶段，不推进
