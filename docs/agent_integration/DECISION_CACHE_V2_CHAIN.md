# Decision Cache v2 Generation Chain

## 生成链
1. Provider Registry 初始化
2. Provider Health Report 输出
3. Providers 按 pair 采样
4. `DecisionAggregator` 融合 ProviderSnapshot
5. 写入 `user_data/agent_runtime/state/decision_cache.json`

## 当前默认 Providers
- `tradingview_mcp`
- `dexpaprika`

## 当前默认 Pairs
- `BTC/USDT`
- `ETH/USDT`

## 输出文件
- `agent_service/reports/provider_health_report.json`
- `user_data/agent_runtime/state/decision_cache.json`
