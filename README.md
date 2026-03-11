# Freqtrade Agent Bridge v2

这是接在 `feature/agent-integration-v1` 之后的第二版。

本版重点：
- 改成“继承你真实主策略”的模板
- 增加 shadow audit / 对账结构
- 增加 live stake only 开关
- 继续保持低风险：默认仍可 shadow 运行
- 为后续 v3 的 exit / stoploss 放开做准备
