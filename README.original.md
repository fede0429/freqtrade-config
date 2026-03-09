# Freqtrade 自适应量化交易系统

> 基于 Freqtrade 框架的现货 + 永续合约自动交易优化包
> 支持 Hyperopt 自动参数优化 → FreqAI 机器学习升级路径

---

## 目录

1. [项目概述](#项目概述)
2. [系统架构](#系统架构)
3. [文件结构](#文件结构)
4. [快速开始](#快速开始)
5. [策略说明](#策略说明)
6. [配置说明](#配置说明)
7. [自动化脚本使用](#自动化脚本使用)
8. [从 dry_run 到实盘](#从-dry_run-到实盘)
9. [FreqAI 升级路径](#freqai-升级路径)
10. [常见问题](#常见问题)

---

## 项目概述

本包是对原始 `freqtrade-config` 仓库的全面优化升级，修复了所有已知 BUG，并添加了：

- **4 个生产级策略**（全部使用 INTERFACE_VERSION 3）
- **现货 + 永续合约双配置**（Binance）
- **自动 Hyperopt 循环脚本**（每周自动优化参数）
- **异步市场扫描工具**（Top 50 多维评分）
- **交易绩效报告生成器**（夏普比率、回撤等关键指标）
- **FreqAI 预备配置**（规则策略 → AI 策略升级路径）

### 核心改进（相比原始仓库）

| 问题 | 原始状态 | 本包状态 |
|------|---------|---------|
| API 版本 | 旧版 `populate_buy_trend` | ✅ INTERFACE_VERSION 3 |
| 卖出逻辑 BUG | min > max，永不触发 | ✅ 修复 |
| 安全漏洞 | 明文密码 admin123 | ✅ CHANGE_ME 占位符 |
| stoploss_on_exchange | false（高风险）| ✅ true |
| 交易对 | 仅 2 对（BTC/ETH）| ✅ 15+ 对 + 动态筛选 |
| 动态筛选 | StaticPairList | ✅ VolumePairList + AgeFilter + SpreadFilter |
| Telegram 通知 | 未开启 | ✅ 完整配置 |
| Docker 健康检查 | 无 | ✅ healthcheck |
| 自动化 | 无 | ✅ Hyperopt 循环脚本 |

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                  自适应量化交易系统架构                          │
│                                                              │
│  ┌─────────────────┐    ┌──────────────────┐                │
│  │  市场扫描         │    │  多时间框架数据    │                │
│  │  market_scanner  │    │  15m + 1h + 4h   │                │
│  └────────┬────────┘    └────────┬─────────┘                │
│           │                      │                           │
│           └──────────┬───────────┘                          │
│                      ▼                                       │
│           ┌────────────────────┐                            │
│           │  AdaptiveMetaStrategy│                           │
│           │  ┌──────────────┐  │                            │
│           │  │ 市场状态检测  │  │                            │
│           │  │ ADX 趋势判断  │  │                            │
│           │  └──────┬───────┘  │                            │
│           │         │          │                            │
│           │  ┌──────▼───────┐  │                            │
│           │  │ 自适应信号权重 │  │                            │
│           │  │ 趋势/震荡切换 │  │                            │
│           │  └──────┬───────┘  │                            │
│           │         │          │                            │
│           │  ┌──────▼───────┐  │                            │
│           │  │ DCA + 动态止损│  │                            │
│           └────────────────────┘                            │
│                      │                                       │
│           ┌──────────▼──────────┐                           │
│           │  Hyperopt 自动循环   │                           │
│           │  每周自动优化参数    │                            │
│           │  SharpeHyperOptLoss │                           │
│           │  SortinoHyperOptLoss│                           │
│           └──────────┬──────────┘                           │
│                      │                                       │
│           ┌──────────▼──────────┐                           │
│           │  绩效报告 + Telegram │                           │
│           │  每日自动报告        │                            │
│           └─────────────────────┘                           │
│                                                              │
│           ┌──────────────────────────────┐                  │
│           │  FreqAI 升级路径（预备阶段）   │                  │
│           │  当前规则 → 混合 → 纯AI       │                  │
│           └──────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 文件结构

```
freqtrade-optimized/
├── config_spot.json            # 现货实盘配置
├── config_futures.json         # 永续合约配置
├── config_freqai.json          # FreqAI 配置片段（预备阶段）
├── docker-compose.yml          # 双服务 Docker 配置
├── README.md                   # 本文档
│
├── strategies/
│   ├── UniversalMACD_V2.py     # UMACD 优化版（现货）
│   ├── UniversalMACD_Futures.py # UMACD 永续版（双向）
│   ├── EnsembleV2Strategy.py   # 集成策略（时间窗口共振）
│   └── AdaptiveMetaStrategy.py # 自适应元策略（核心推荐）
│
└── scripts/
    ├── auto_hyperopt.sh         # 自动 Hyperopt 循环
    ├── market_scanner.py        # 市场扫描工具
    └── performance_report.py    # 绩效报告生成器
```

---

## 快速开始

### 前置条件

- Docker + Docker Compose 已安装
- Binance API Key（现货 or 期货）
- Telegram Bot Token + Chat ID（推荐）

### 步骤 1：复制文件到你的项目

```bash
# 将 strategies/ 目录复制到你的 user_data/strategies/
cp strategies/*.py /your-project/user_data/strategies/

# 将配置文件复制到 user_data/
cp config_spot.json config_futures.json /your-project/user_data/

# 将 docker-compose.yml 替换原有文件
cp docker-compose.yml /your-project/
```

### 步骤 2：配置敏感信息

编辑 `config_spot.json`，替换所有 `CHANGE_ME` 占位符：

```json
"exchange": {
    "name": "binance",
    "key": "你的_API_KEY",          // ← 替换
    "secret": "你的_API_SECRET"      // ← 替换
},
"telegram": {
    "token": "你的_BOT_TOKEN",       // ← 替换
    "chat_id": "你的_CHAT_ID"        // ← 替换
},
"api_server": {
    "jwt_secret_key": "随机32位字符串",  // ← 替换
    "username": "你的用户名",            // ← 替换
    "password": "你的强密码"             // ← 替换
}
```

**推荐方式：使用 .env 文件（更安全）**

```bash
# 创建 .env 文件（已在 .gitignore 中）
cat > .env << EOF
SPOT_API_KEY=your_binance_spot_api_key
SPOT_API_SECRET=your_binance_spot_api_secret
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
API_PASSWORD=your_strong_password
JWT_SECRET=your_32_char_random_string
EOF
```

### 步骤 3：下载历史数据

```bash
# 下载 6 个月数据用于回测和 Hyperopt
docker compose run --rm freqtrade-spot \
    download-data \
    --config /freqtrade/user_data/config_spot.json \
    --timerange 20240601- \
    --timeframes 15m 1h 4h
```

### 步骤 4：回测验证

```bash
# 回测 AdaptiveMetaStrategy（推荐起点）
docker compose run --rm freqtrade-spot \
    backtesting \
    --config /freqtrade/user_data/config_spot.json \
    --strategy AdaptiveMetaStrategy \
    --timerange 20240601-

# 回测 UniversalMACD V2（更保守）
docker compose run --rm freqtrade-spot \
    backtesting \
    --config /freqtrade/user_data/config_spot.json \
    --strategy UniversalMACD_V2
```

### 步骤 5：Dry Run 验证（重要！）

```bash
# 启动现货 dry_run
docker compose up -d freqtrade-spot

# 查看日志
docker compose logs -f freqtrade-spot
```

**至少运行 7 天 dry_run，确认系统稳定后再切实盘。**

---

## 策略说明

### 1. AdaptiveMetaStrategy（推荐主策略）

**适用场景：** 所有市场条件（趋势 + 震荡自适应）

**核心特性：**
- 市场状态检测（ADX > 25 = 趋势市，否则 = 震荡市）
- 趋势市场：UMACD + Supertrend 动量跟随
- 震荡市场：RSI + 布林带均值回归
- 多时间框架确认（15m 主框架 + 1h + 4h 趋势过滤）
- DCA 加仓（最多 2 次，跌 3% 和 7% 时加仓）

**参数优化：**
```bash
freqtrade hyperopt \
    --strategy AdaptiveMetaStrategy \
    --hyperopt-loss SharpeHyperOptLoss \
    --spaces buy sell roi stoploss trailing \
    --epochs 500
```

**风险等级：** 中等（适合 500-2000 USDT）

---

### 2. UniversalMACD_V2（稳健现货策略）

**适用场景：** 现货，趋势市场效果最佳

**核心特性：**
- UMACD（EMA12/EMA26 比值偏差）作为主信号
- RSI 双向过滤（避免极端超买/超卖陷阱）
- Volume 过滤（只在放量时入场）
- EMA200 趋势过滤（可选，避免逆势）
- 动态止损（盈利梯度锁定）

**推荐时间框架：** 15m

**风险等级：** 低（保守参数）

---

### 3. UniversalMACD_Futures（永续合约版）

**适用场景：** 永续合约双向交易

**核心特性：**
- 继承 V2 所有功能
- can_short = True（支持做空）
- 做空信号：UMACD 进入正值超买区 + RSI 超买
- 更严格止损（硬止损 -7%）
- 24 小时超时止损（节省资金费）

**注意：** 使用前必须设置 `leverage_config`，建议最高 3x

**风险等级：** 中高（永续合约有爆仓风险）

---

### 4. EnsembleV2Strategy（集成共振策略）

**适用场景：** 现货，需要更高信号质量

**核心创新：时间窗口共振**
- UMACD 信号出现后，在 N 根 K 线内等待 Volume 突破确认
- 不要求同一根 K 线同时满足，减少错过的信号
- 修复了原始 EnsembleLooseStrategy 的所有 BUG

**适用情景：** 希望高胜率、低频率的交易风格

**风险等级：** 低（严格双重确认）

---

## 配置说明

### config_spot.json 关键参数

| 参数 | 当前值 | 说明 |
|------|--------|------|
| `dry_run` | `true` | 先用 dry_run 验证 7 天 |
| `max_open_trades` | `5` | 最多同时 5 个仓位 |
| `stake_amount` | `"unlimited"` | 自动分配资金 |
| `tradable_balance_ratio` | `0.7` | 使用总资金的 70% |
| `stoploss_on_exchange` | `true` | 交易所止损（网络断开时保护）|

### config_futures.json 关键参数

| 参数 | 当前值 | 说明 |
|------|--------|------|
| `trading_mode` | `"futures"` | 永续合约模式 |
| `margin_mode` | `"isolated"` | 隔离保证金（更安全）|
| `max_open_trades` | `3` | 更保守（永续风险高）|
| `tradable_balance_ratio` | `0.5` | 只用 50% 资金 |

### 交易保护（Protections）

已配置以下保护机制（适合 500-2000 USDT 规模）：

| 保护类型 | 作用 |
|---------|------|
| `StoplossGuard` | 24 小时内 2 次止损后暂停 4 根 K 线 |
| `MaxDrawdown` | 48 小时内回撤超 15% 暂停 12 根 K 线 |
| `CooldownPeriod` | 每次止损后冷却 2 根 K 线 |
| `LowProfitPairs` | 60 根 K 线内没有盈利的交易对暂停 60 根 K 线 |

---

## 自动化脚本使用

### auto_hyperopt.sh — 每周自动优化

```bash
# 设置可执行权限
chmod +x scripts/auto_hyperopt.sh

# 手动运行（指定策略）
STRATEGY=AdaptiveMetaStrategy bash scripts/auto_hyperopt.sh

# 设置 cron 每周日凌晨 2 点自动运行
crontab -e
# 添加：0 2 * * 0 cd /path/to/project && bash scripts/auto_hyperopt.sh
```

脚本会自动：
1. 下载最新 180 天历史数据
2. 用 3 种 Loss 函数（Sharpe/Sortino/Calmar）分别优化
3. 保存最优参数到 `reports/` 目录
4. 运行回测验证
5. 生成 Markdown 报告
6. 发送 Telegram 通知

### market_scanner.py — 市场扫描

```bash
# 扫描 Top 50 并发送 Telegram
python scripts/market_scanner.py --top 50 --telegram

# 只显示评分 >= 70 的机会
python scripts/market_scanner.py --min-score 70

# 导出 JSON 结果
python scripts/market_scanner.py --output scan_$(date +%Y%m%d).json

# 静默模式（只输出 JSON）
python scripts/market_scanner.py --json --quiet
```

### performance_report.py — 绩效报告

```bash
# 全量报告（所有历史数据）
python scripts/performance_report.py

# 最近 7 天报告
python scripts/performance_report.py --days 7

# 保存为 Markdown 文件
python scripts/performance_report.py --output reports/weekly_$(date +%Y%m%d).md

# 每日自动报告 cron 设置（每天早上 8 点）
# 0 8 * * * cd /path/to/project && python scripts/performance_report.py --days 1 --telegram
```

---

## 从 dry_run 到实盘

### 阶段化迁移步骤

**阶段 1：Dry Run 验证（1-2 周）**

```bash
# 确认 dry_run: true
# 启动并观察 7-14 天
docker compose up -d freqtrade-spot
docker compose logs -f freqtrade-spot
```

观察指标：
- 每天至少有 1-3 次交易信号
- 胜率 > 50%
- 最大回撤 < 15%

**阶段 2：运行 Hyperopt 优化参数**

```bash
# 先下载数据
docker compose run --rm freqtrade-spot \
    download-data --config /freqtrade/user_data/config_spot.json \
    --timerange 20240601- --timeframes 15m 1h 4h

# 运行 Hyperopt
bash scripts/auto_hyperopt.sh
```

**阶段 3：小资金实盘（100-200 USDT）**

1. 修改 `config_spot.json`：
   ```json
   "dry_run": false,
   "stake_amount": "unlimited",
   "tradable_balance_ratio": 0.5,
   "max_open_trades": 3
   ```
2. 替换所有 `CHANGE_ME` 为真实值
3. 启动并密切监控

**阶段 4：逐步扩大规模**

- 实盘运行 2 周，确认实盘与 dry_run 结果接近
- 每次增加 50-100 USDT，最多增加 3 次
- 定期（每周）运行 auto_hyperopt.sh 更新参数

### 安全检查清单

在切换到实盘前，确认以下所有项目：

- [ ] 所有 `CHANGE_ME` 已替换为真实值
- [ ] API Key 权限已设置为"仅交易"（不允许提现）
- [ ] Telegram 通知工作正常
- [ ] `stoploss_on_exchange: true`
- [ ] Docker 健康检查正常（`docker compose ps`）
- [ ] dry_run 至少运行 7 天，结果可接受
- [ ] 回测结果夏普比率 > 1.0，最大回撤 < 20%

---

## FreqAI 升级路径

### 升级时间表

```
阶段 0（当前）：规则驱动 + Hyperopt 自动优化
  └─ AdaptiveMetaStrategy（规则策略）
  └─ auto_hyperopt.sh（每周自动优化）

阶段 1（4-8 周后）：收集真实交易数据
  └─ 积累至少 200-500 笔真实交易记录

阶段 2（8-12 周后）：FreqAI 混合模式
  └─ 将 config_freqai.json 中的配置合并到主配置
  └─ 策略中添加 FreqAI 预测置信度过滤
  └─ 并行运行：规则策略 vs FreqAI 混合策略

阶段 3（3 个月后）：纯 FreqAI 策略
  └─ 以 FreqAI 预测为主信号
  └─ 规则条件作为辅助过滤
  └─ 自适应再训练（每 168 小时）
```

### 快速接入 FreqAI

1. **确认 LightGBM 可用：**
   ```bash
   docker exec freqtrade-spot python -c "import lightgbm; print('LightGBM OK')"
   ```

2. **将 FreqAI 配置合并到 config_spot.json：**
   ```bash
   # 提取 freqai 配置块
   cat config_freqai.json | python3 -c "
   import json, sys
   data = json.load(sys.stdin)
   print(json.dumps({'freqai': data['freqai']}, indent=2))
   "
   # 手动粘贴到 config_spot.json
   ```

3. **修改策略（按 config_freqai.json 中的示例代码）**

4. **运行 FreqAI 回测：**
   ```bash
   docker compose run --rm freqtrade-spot \
       backtesting \
       --config /freqtrade/user_data/config_spot.json \
       --strategy AdaptiveMetaStrategy \
       --freqaimodel LightGBMRegressor
   ```

---

## 常见问题

### Q1：策略没有产生交易信号

**原因：** 参数区间太严格，或数据不足

**解决：**
```bash
# 检查最近的指标值
docker exec freqtrade-spot freqtrade list-data --config /freqtrade/user_data/config_spot.json

# 运行 analyze-entry-exit 查看信号
freqtrade analyze-entry-exit \
    --config user_data/config_spot.json \
    --strategy AdaptiveMetaStrategy \
    --timerange 20241201-
```

### Q2：Hyperopt 运行太慢

**解决：**
1. 减少 epochs：`--epochs 100`
2. 增加并发：`-j -1`（使用全部 CPU）
3. 缩小数据范围：`--timerange 20241001-`
4. 减少优化空间：`--spaces buy sell`（先优化买卖，后优化 ROI）

### Q3：实盘和 dry_run 结果差异大

**可能原因：**
- 滑点（limit 订单未成交）
- K 线数据延迟
- 手续费影响

**解决：** 在 config 中调整：
```json
"entry_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1
}
```

### Q4：Docker 容器频繁重启

**诊断：**
```bash
docker compose logs freqtrade-spot --tail 50
docker stats freqtrade-spot  # 检查内存
```

**常见原因：** 内存不足（GodStra 策略的 `add_all_ta_features` 非常耗内存）

**解决：** 不要使用 GodStra 策略；如需增加内存，修改 docker-compose.yml 中的 `mem_limit`

### Q5：永续合约杠杆如何设置

在 `config_futures.json` 中添加：
```json
"leverage_config": {
    "default": 3,
    "BTC/USDT:USDT": 3,
    "ETH/USDT:USDT": 3
}
```

**强烈建议：** 杠杆不超过 3x，最安全的是 1x（等同现货）

### Q6：如何添加更多交易对

修改 `config_spot.json` 中的 `pairlists`：

```json
"pairlists": [
    {
        "method": "VolumePairList",
        "number_assets": 30,   // ← 增加这个数字
        "sort_key": "quoteVolume"
    }
]
```

或者手动将交易对添加到 `pair_whitelist`。

### Q7：Telegram Bot 如何创建

1. 在 Telegram 中找到 `@BotFather`
2. 发送 `/newbot`，按提示创建
3. 保存 `token`
4. 给 Bot 发消息，然后访问：
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. 从响应中找到 `chat_id`

---

## 风险声明

**重要：本系统仅供教育和研究目的。加密货币交易存在极高风险，可能导致全部资金损失。在使用前请确保：**

1. 充分理解策略逻辑
2. 在 dry_run 模式下充分验证
3. 只投入你能承受损失的资金
4. 永续合约有爆仓风险，请谨慎使用杠杆

---

*最后更新：2026-03-04*
