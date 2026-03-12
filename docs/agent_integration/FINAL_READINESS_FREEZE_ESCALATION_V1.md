# Final Readiness Freeze / Escalation v1

## 新增能力
- final readiness freeze policy
- escalation reason summary
- pair-level freeze / escalate verdict
- escalation report

## 配置文件
- `user_data/config/freeze_escalation_policy.json`

## 输出文件
- `agent_service/reports/freeze_escalation_policy_report.json`
- `agent_service/reports/escalation_report.json`

## 动作含义
- `freeze_pair`: 当前 pair 冻结
- `escalate_for_review`: 提交人工复核
- `ready_for_snapshot`: 可进入收口快照候选
- `continue_shadow`: 保持影子阶段
