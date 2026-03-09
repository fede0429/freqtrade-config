# STEP 3 - 风控层独立化

这一阶段把风控从“策略里的零散参数”提升为“系统级放行规则”。

## 目标

让交易系统从：

- 策略想开仓就开仓

升级为：

- 策略发信号
- 风控层审查
- 执行层决定 allow / reduce_only / block

## 新增结构

- `config/risk/base/common.json`：通用风控底座
- `config/risk/base/spot.json`：现货约束
- `config/risk/base/futures.json`：期货约束
- `config/risk/env/paper.json`：模拟盘阈值
- `config/risk/env/prod.json`：实盘阈值
- `config/risk/runtime/*.json`：最终风险画像
- `services/risk/risk_engine.py`：统一风险决策引擎
- `scripts/validate/validate_risk_governance.py`：风险配置检查器

## 四层风控

### 1. 账户级
- 日亏损阈值
- 周亏损阈值
- 最大回撤阈值
- 连续亏损熔断

### 2. 策略级
- 单策略最大资金占用
- 单策略最大开仓上限

### 3. 标的级
- 单币最大敞口
- 相关性桶最大敞口

### 4. 市场级
- 高波动禁入
- funding rate 过高禁入
- 大盘急跌时 reduce_only
- scanner 未批准时禁止新开单

## 决策模式

风险引擎输出三种结果：

- `allow`：允许交易
- `reduce_only`：只允许减仓，不允许加仓/新开仓
- `block`：完全阻断

## 当前阶段说明

这一步已经完成的是：

- 风险配置独立化
- 风险画像渲染脚本
- 风险校验脚本
- 风险决策引擎样板

这一步还没有完成的是：

- 把风险引擎真正挂入 Freqtrade 下单链路
- 把 scanner 的 regime / risk_flags 正式接入风险引擎
- 把 reporter 的日报/周报接入风控事件统计

## 运行方式

渲染风险画像：

```bash
bash scripts/bootstrap/render_all_risk_profiles.sh
```

校验风险画像：

```bash
python3 scripts/validate/validate_risk_governance.py config/risk/runtime/spot.paper.json
python3 scripts/validate/validate_risk_governance.py config/risk/runtime/futures.prod.json
```

## 工作室建议

对于你的工作室主线，建议先这样用：

- 现货 paper：作为默认试运行环境
- 现货 prod：比 paper 更紧的日亏损/回撤限制
- 期货 paper：先禁用 DCA
- 期货 prod：更低总敞口、更高现金预留、更严格 stoploss
