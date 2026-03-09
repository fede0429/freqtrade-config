# Step 4 - 策略生产化治理

这一步把“策略文件存在”升级成“策略有生命周期、参数版本、准入门槛、发布画像”。

## 新增能力

1. **策略注册表**
   - 所有可管理策略统一登记在 `strategies/registry/strategy_registry.json`
   - 记录市场类型、代码路径、参数版本、生命周期阶段、升级门槛

2. **参数版本化**
   - 每个策略都有单独参数目录，例如：
     - `strategies/params/AdaptiveMetaStrategy/v1.0.0/`
   - 其中拆分成：
     - `base.json`
     - `paper.json`
     - `prod.json`

3. **阶段化治理**
   - `candidate`：研究候选，不能进入生产
   - `dry_run`：运行观察，不接真实资金
   - `canary`：小流量观察
   - `production`：正式生产
   - `retired`：归档停用

4. **升级门槛**
   - 回测天数
   - 最大回撤
   - profit factor
   - 胜率
   - dry-run 时长
   - canary 时长

## 当前策略路线

- `UniversalMACD_V2`：production 基线
- `AdaptiveMetaStrategy`：canary 主研究线
- `UniversalMACD_Futures`：dry-run 观察线
- `TrendEMAStrategy`：candidate 研究线

## 验证

```bash
python3 scripts/validate/validate_strategy_governance.py .
python3 scripts/bootstrap/render_strategy_manifest.py
```

## 运营含义

以后你的工作室不再是“改个策略文件就上生产”，而是必须经过：

`candidate -> dry_run -> canary -> production`

并且每一步都要有可核查的参数版本和升级门槛。
