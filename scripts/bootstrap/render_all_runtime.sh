#!/usr/bin/env bash
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
python3 "$ROOT/scripts/bootstrap/render_config.py" spot paper dynamic config/runtime/spot.paper.dynamic.json
python3 "$ROOT/scripts/bootstrap/render_config.py" spot prod static config/runtime/spot.prod.static.json
python3 "$ROOT/scripts/bootstrap/render_config.py" futures paper dynamic config/runtime/futures.paper.dynamic.json
python3 "$ROOT/scripts/bootstrap/render_config.py" futures prod static config/runtime/futures.prod.static.json
echo "[OK] rendered example runtime configs"
