# Bridge Snapshot v1

这是 bridge 主线的第一份收口版。

## 已收口能力
- AgentBridgeStrategy 统一版
- decision schema v2 兼容
- provider health / stale guard
- bridge runtime trace
- stake / exit / stoploss / roi / entry_confirm 全量 trace
- replay compare 汇总

## 推荐使用方式
- 以后以这份收口包为 bridge 主参考
- 旧的相关 bridge 增量包可不再单独维护
- 下一步做 `current_full_snapshot_v1`
