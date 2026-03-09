# STEP 9 - Scanner 真实数据接线

本阶段目标：把 scanner 从 mock 模式推进到真实数据接线前的可验证状态。

## 本步完成内容

1. `apps/scanner/market_scanner.py` 升级为 v4，支持三种 source:
   - `mock`
   - `fixture`
   - `live`
2. 新增 `services/scanner/market_data.py`
   - 负责从 OHLCV 计算 liquidity / volume_ratio / momentum / volatility
   - 支持 fixture 和 live 数据源
3. 在 `config/scanner/base/*.json` 中增加 `source` 配置
4. 新增本地 OHLCV fixture，供离线验证整条扫描链
5. 新增 `scripts/validate/validate_scanner_data_source.py`

## 为什么先做 fixture 再做 live

当前容器环境不能保证外网和交易所 API 可达，所以本步先把：

- 数据源契约
- 计算逻辑
- 输出结构
- 校验脚本

全部固定下来。

这样你切到真实 Binance / Bybit / OKX 时，不需要再改 scanner 主体，只需要切 source=live 并准备好 ccxt。

## Live 模式依赖

live 模式要求：

- 已安装 `ccxt`
- 交易所 API 网络可达
- `config/runtime/*.json` 中 exchange 配置正确

运行示例：

```bash
PYTHONPATH=. python3 apps/scanner/market_scanner.py \
  --profile config/scanner/runtime/spot.paper.json \
  --source live \
  --output reports/scanner/latest_scan.json
```

## Fixture 模式示例

```bash
PYTHONPATH=. python3 apps/scanner/market_scanner.py \
  --profile config/scanner/runtime/spot.paper.json \
  --source fixture \
  --fixture data/fixtures/scanner/binance_spot_ohlcv_sample.json \
  --output reports/scanner/latest_scan_step9.json
```

## 当前阶段性结论

第 9 阶段已经完成：

- scanner 数据源抽象
- OHLCV 指标计算
- fixture 离线验证
- live 模式代码接线

还没完成：

- 在当前环境下实际连接交易所并验证 live 返回
- 将 live scanner 定时接入 paper 日常运行
- 将 scanner 输出直接注入 trader 启动链
