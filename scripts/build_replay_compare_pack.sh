#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[replay-pack] python3 or python is required" >&2
  exit 1
fi

(
  cd "${ROOT_DIR}"
  "${PYTHON_CMD}" agent_service/apps/build_replay_compare_pack/main.py
)
