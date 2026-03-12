# Decision Aggregator Integration v1

本包把 `decision_aggregator.py` 正式接入到 `decision_cache` 生成链。

## 本版目标
- 用统一 Provider 输出生成 `decision_cache.json`
- 给桥接层提供稳定的 schema v2 输入
- 保留对旧版扁平字段的桥接兼容
- 为后续接入更多 Providers 打好入口

## 新增内容
- `build_decision_cache_v2.py`
- `provider_registry.py`
- `provider_health_report.py`
- `sample_provider_run.py`
- 文档与提交建议

## 推荐集成位置
agent_service/
  aggregator/
  providers/
  reports/
user_data/
  agent_runtime/state/
