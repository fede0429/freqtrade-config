# Integration Plan

## Stage 1: shadow mode
- 提交到独立分支
- 启用 AgentBridgeStrategy
- shadow_mode = true
- enabled_callbacks 全部 false
- 只读 decision_cache + 写 shadow_log

## Stage 2: live stake only
- stake = true
- 其余仍 false

## Stage 3: live exit
- exit = true

## Stage 4: live stoploss
- stoploss = true

## Stage 5: optional roi
- roi = true
