# Provider Rollout / Pair-level Provider Enablement v1

## 新增能力
- 逐 pair 控制启用哪些 provider
- 逐 pair 设置 required providers
- 逐 pair rollout stage
- 逐 pair 强制启用 / 禁用 provider

## 当前配置文件
- `user_data/config/provider_rollout.json`

## 输出
- `agent_service/reports/provider_health_report.json`
- `agent_service/reports/provider_rollout_report.json`
- `user_data/agent_runtime/state/decision_cache.json`

## 推荐用法
- BTC/USDT: 作为 full readonly pair
- ETH/USDT: 先只启用 technical provider
- SOL/USDT: 作为候选 pair，在 shadow 中观察
