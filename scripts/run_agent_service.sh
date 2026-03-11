#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

resolve_python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    printf '%s\n' "${PYTHON_BIN}"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    printf '%s\n' "python"
    return
  fi
  echo "[agent] python3 or python is required" >&2
  exit 1
}

run_once() {
  (
    cd "${ROOT_DIR}"
    "${PYTHON_CMD}" agent_service/apps/build_decision_cache/main.py
  )
}

PYTHON_CMD="$(resolve_python_bin)"
REFRESH_INTERVAL="${AGENT_REFRESH_INTERVAL_SECONDS:-30}"
MODE="${1:-once}"

if [[ "${MODE}" == "--watch" ]]; then
  echo "[agent] watch mode enabled (${REFRESH_INTERVAL}s refresh)"
  while true; do
    echo "[agent] refreshing decision cache"
    run_once
    sleep "${REFRESH_INTERVAL}"
  done
fi

echo "[agent] building decision cache"
run_once
echo "[agent] done"
