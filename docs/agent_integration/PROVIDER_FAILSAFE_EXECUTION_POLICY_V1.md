# Provider Failsafe / Execution Policy v1

## 新增能力
- provider minimum count gate
- pair-level callback rollout control
- pair-level fallback mode
- execution policy report

## 配置文件
- `user_data/config/execution_policy.json`

## 输出文件
- `agent_service/reports/execution_policy_report.json`

## 当前示例
- `BTC/USDT`: 需要至少 2 个 provider，允许全 callback
- `ETH/USDT`: 允许 roi=false
- `SOL/USDT`: 禁止 stake 和 roi，只做 shadow candidate pair
