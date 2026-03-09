# STEP2 配置治理与密钥隔离

## 本步目标
把配置从“单个大 json”重构成“基础层 + 环境层 + 交易对选择层 + secrets 层”。

## 新规则
1. **运行时只认 `config/runtime/*.json`**
2. **基础模板放在 `config/base/`**
3. **环境差异放在 `config/env/`**
4. **交易对选择只能二选一：`static` 或 `dynamic`**
5. **密钥只放在 `config/secrets/.env`，不再写入仓库内 json**

## 目录说明
- `config/base/common.json`：现货/期货共用设置
- `config/base/spot.json`：现货专属设置
- `config/base/futures.json`：期货专属设置
- `config/env/dev.json`：本地开发
- `config/env/paper.json`：模拟盘
- `config/env/prod.json`：实盘
- `config/pairlists/*.json`：交易对来源策略
- `config/runtime/*.json`：渲染后的运行配置
- `config/secrets/.env.example`：密钥模板

## 本步已经处理的问题
- 把旧的 `config_spot.json` / `config_futures.json` 拆成片段
- 把 pair whitelist 和 VolumePairList 的意图分离
- 给 docker 提供 `.env` 注入入口
- 增加了配置渲染脚本和治理校验脚本

## 你现在的使用流程
1. 复制 `config/secrets/.env.example` 为 `config/secrets/.env`
2. 填入真实密钥
3. 运行：`scripts/bootstrap/render_all_runtime.sh`
4. 校验：
   - `scripts/validate/validate_config_governance.py config/runtime/spot.paper.dynamic.json`
   - `scripts/validate/validate_config_governance.py config/runtime/futures.paper.dynamic.json`
5. 再启动 docker compose

## 当前建议的工作室默认值
- Spot：`paper + dynamic + AdaptiveMetaStrategy`
- Futures：`paper + dynamic + UniversalMACD_Futures`

## 下一步预告
第 3 步将把风控从策略/配置分散参数升级为独立治理层。
