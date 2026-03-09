#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python3 scripts/bootstrap/render_risk_profile.py spot paper config/risk/runtime/spot.paper.json
python3 scripts/bootstrap/render_risk_profile.py spot prod config/risk/runtime/spot.prod.json
python3 scripts/bootstrap/render_risk_profile.py futures paper config/risk/runtime/futures.paper.json
python3 scripts/bootstrap/render_risk_profile.py futures prod config/risk/runtime/futures.prod.json

echo "[OK] rendered all risk profiles"
