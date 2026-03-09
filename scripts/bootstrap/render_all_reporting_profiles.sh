#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT_DIR/scripts/bootstrap/render_reporting_profile.py" spot paper "$ROOT_DIR/config/reporting/runtime/spot.paper.json"
python3 "$ROOT_DIR/scripts/bootstrap/render_reporting_profile.py" spot prod "$ROOT_DIR/config/reporting/runtime/spot.prod.json"
python3 "$ROOT_DIR/scripts/bootstrap/render_reporting_profile.py" futures paper "$ROOT_DIR/config/reporting/runtime/futures.paper.json"
python3 "$ROOT_DIR/scripts/bootstrap/render_reporting_profile.py" futures prod "$ROOT_DIR/config/reporting/runtime/futures.prod.json"
echo "[OK] reporting profiles rendered"
