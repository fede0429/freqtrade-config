# Staged Rollout V2

## 这一步建议
- 继续在 `feature/agent-integration-v1` 上提交
- 先把 `AgentBridgeStrategy.py` 改成真实主策略继承
- 保持 `shadow_mode=true`
- 即使 `stake=true`，也先 dry-run

## 推荐顺序
1. 先提交这版代码到分支
2. 把 BaseStrategy 替换成你真实主策略
3. dry-run 观察：
   - stake_decision_trace.jsonl
   - stake_apply_trace.jsonl
4. 如果 dry-run 正常，再考虑关闭 `shadow_mode`
