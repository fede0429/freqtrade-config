# Provider / Aggregator Snapshot v1

这是 provider / aggregator 主线的第一份收口版。

## 已收口能力
- provider 基础接口与两个只读 provider 骨架
- registry / rollout
- confidence / weighting
- execution policy
- anomaly guard
- cooldown guard
- governance gatekeeper
- rollout state machine
- readiness / handoff / review
- freeze / escalation
- decision cache v2 生成链

## 推荐使用方式
- 以后以这份收口包为 provider / aggregator 主参考
- 旧的相关增量包可不再单独维护
- 下一步做 `bridge_snapshot_v1`
