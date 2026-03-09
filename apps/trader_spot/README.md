# trader_spot

现货交易应用入口。

当前正式启动路径：

- `scripts/deploy/start_spot_paper.sh`
- `scripts/deploy/start_spot_prod.sh`

启动前会先做 preflight，只有通过后才会进入 `armed` 状态。
真正执行 Docker 启动时，应通过：

```bash
PYTHONPATH=. python3 scripts/deploy/start_trader.py config/release/runtime/spot.paper.json --execute
```

关键输入：

- 运行时交易配置：`config/runtime/spot.*.json`
- 运行时风险画像：`config/risk/runtime/spot.*.json`
- scanner 输出：`reports/scanner/latest_scan*.json`
- 日报：`reports/operations/daily/*.json`
- 部署清单：`strategies/registry/deployment_manifest.json`
