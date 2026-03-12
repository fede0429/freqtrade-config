# News Signal Snapshot v1

这是 news 主线的第一份收口版。

## 已收口能力
- source registry / trust / weight policy
- llm client
- official / exchange status / media / social / fallback providers
- event normalize / dedupe
- event -> snapshot mapper
- news rollout config
- news 接入 decision cache 生成链
- news governance overlay
- news review / ops handoff
- news quality / health metrics

## 推荐使用方式
- 以后以这份收口包为 news 主参考
- 旧的 news 相关增量包可不再单独维护
- 后续如需整合进总快照，建议做 `current_full_snapshot_v2`
