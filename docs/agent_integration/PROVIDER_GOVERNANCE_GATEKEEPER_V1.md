# Provider Governance Gatekeeper v1

## 新增能力
- pair-level governance gatekeeper
- provider / anomaly / cooldown / execution 汇总审批
- final trading mode
- governance block reasons
- approval summary report

## 配置文件
- `user_data/config/governance_policy.json`

## 输出文件
- `agent_service/reports/governance_policy_report.json`
- `agent_service/reports/approval_summary_report.json`

## 当前示例
- `BTC/USDT`: 审批通过后进入 `paper_candidate`
- `ETH/USDT`: 被阻断时进入 `technical_shadow`
- `SOL/USDT`: 若 active cooldown 则直接阻断
