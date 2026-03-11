#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
STATE_DIR="${ROOT_DIR}/user_data/agent_runtime/state"
AUDIT_ROOT="${ROOT_DIR}/user_data/agent_runtime/audit"

if [[ "${1:-}" == "--" ]]; then
  shift
fi

if [[ "$#" -eq 0 ]]; then
  echo "Usage: scripts/run_hybrid_stack.sh <freqtrade command...>" >&2
  echo "Example: scripts/run_hybrid_stack.sh freqtrade trade --config user_data/config.json --strategy AgentBridgeStrategy" >&2
  exit 1
fi

if [[ -z "${AGENT_RUN_ID:-}" ]]; then
  AGENT_RUN_ID="run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
fi
export AGENT_RUN_ID
mkdir -p "${STATE_DIR}" "${AUDIT_ROOT}/${AGENT_RUN_ID}"
printf '%s\n' "${AGENT_RUN_ID}" > "${STATE_DIR}/current_run_id.txt"

echo "[stack] AGENT_RUN_ID=${AGENT_RUN_ID}"

cleanup() {
  if [[ -n "${AGENT_WATCH_PID:-}" ]]; then
    kill "${AGENT_WATCH_PID}" >/dev/null 2>&1 || true
    wait "${AGENT_WATCH_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "[stack] step 1: build initial decision cache"
bash "${SCRIPT_DIR}/run_agent_service.sh"

echo "[stack] step 2: keep decision cache fresh in the background"
bash "${SCRIPT_DIR}/run_agent_service.sh" --watch &
AGENT_WATCH_PID=$!

echo "[stack] step 3: start freqtrade with agent bridge"
(
  cd "${ROOT_DIR}"
  "$@"
)
