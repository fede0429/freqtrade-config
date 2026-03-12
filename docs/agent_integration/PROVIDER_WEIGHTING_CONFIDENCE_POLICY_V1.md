# Provider Weighting / Confidence Policy v1

## 新增能力
- provider 权重
- pair-level confidence threshold
- pair-level risk threshold
- pair-level risk bias
- degraded provider score neutralization

## 配置文件
- `user_data/config/confidence_policy.json`

## 输出文件
- `agent_service/reports/confidence_policy_report.json`

## 当前示例
- `BTC/USDT`: 更高 entry threshold，更激进 trend rr
- `ETH/USDT`: 更严格 max_risk_score，并增加 risk bias
- `SOL/USDT`: 更高置信度门槛，更保守 stake cap
