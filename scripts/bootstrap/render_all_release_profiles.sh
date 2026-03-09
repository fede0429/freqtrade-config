#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python3 scripts/bootstrap/render_release_profile.py spot paper config/release/runtime/spot.paper.json
python3 scripts/bootstrap/render_release_profile.py spot prod config/release/runtime/spot.prod.json
python3 scripts/bootstrap/render_release_profile.py futures paper config/release/runtime/futures.paper.json
python3 scripts/bootstrap/render_release_profile.py futures prod config/release/runtime/futures.prod.json
echo "[OK] rendered release runtime profiles"
