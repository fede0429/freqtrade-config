# STEP5 - 市场扫描器重构

本步目标：把扫描器从旁支脚本升级成交易前置层。

## 新增内容
- `config/scanner/`：扫描配置与运行时画像
- `services/scanner/`：扫描规则、类型、加载器
- `apps/scanner/market_scanner.py`：标准化输出入口
- `scripts/bootstrap/render_all_scanner_profiles.sh`：渲染全部扫描画像
- `scripts/validate/validate_scanner_governance.py`：治理校验器

## 输出契约
扫描器现在输出统一 JSON：
- `tradable_pairs`
- `market_regime`
- `risk_flags`
- `ranking_scores`
- `pair_decisions`

## 当前阶段说明
当前第5步先固定契约和治理层，`market_scanner.py` 使用 `--mock` 跑样本数据，先让风控层、trader、reporter 都能接统一接口。
下一步再把真实交易所数据源替换回去。
