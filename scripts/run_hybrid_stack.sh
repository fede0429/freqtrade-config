#!/usr/bin/env bash
set -euo pipefail
echo "[stack] step 1: refresh agent decision cache"
bash scripts/run_agent_service.sh
echo "[stack] step 2: start freqtrade in dry-run or trade mode"
echo "Example:"
echo "freqtrade trade --config user_data/config.json --strategy AgentBridgeStrategy"
