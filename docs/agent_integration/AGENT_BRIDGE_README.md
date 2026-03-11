# Freqtrade Agent Bridge v1

这是一版“先分支、后整合”的接入骨架，目标是把已经开发到 v24 的 agent sidecar
以最小风险方式接入现有 Freqtrade 仓库，而不是直接改爆主运行策略。

## 本版内容
- AgentBridgeStrategy.py 骨架
- decision_cache.json 协议
- agent_overlay.json 配置
- hybrid stack 启动脚本
- sidecar 决策缓存构建器
- shadow 模式日志输出

## 建议分支
feature/agent-integration-v1

## 建议先提交到分支的目录
- user_data/strategies/AgentBridgeStrategy.py
- user_data/agent_runtime/
- user_data/config/agent_overlay.json
- scripts/run_agent_service.sh
- scripts/run_hybrid_stack.sh
- agent_service/apps/build_decision_cache/
