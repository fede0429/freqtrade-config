# 全体代码对齐优化版

这次不是新增单点 callback，而是把 v1-v8 的桥接逻辑统一成一版长期维护结构。

## 已对齐内容
- 统一 callback 开关读取
- 统一 pair allowlist
- 统一 cache freshness 判断
- 统一 audit trace 命名
- 统一 replay compare 汇总
- 统一 overlay 配置

## 建议执行顺序
1. 替换真实主策略继承
2. 保持 shadow_mode=true
3. dry-run
4. 执行 replay compare
5. 再决定是否逐项关闭 shadow
