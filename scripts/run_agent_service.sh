#!/usr/bin/env bash
set -euo pipefail
echo "[agent] building decision cache"
python agent_service/apps/build_decision_cache/main.py
echo "[agent] done"
