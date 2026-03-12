# Provider Observability / Anomaly Guard v1

## 新增能力
- provider observability snapshot
- pair/provider anomaly guard
- provider score drift detection
- provider latency threshold
- anomaly policy report

## 配置文件
- `user_data/config/anomaly_policy.json`

## 输出文件
- `agent_service/reports/provider_observability_report.json`
- `agent_service/reports/anomaly_policy_report.json`

## 当前示例
- `BTC/USDT`: 更低 latency 上限，更严格 score drift
- `SOL/USDT`: 更严格 latency 上限，并允许 latency 直接阻断
