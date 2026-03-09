#!/usr/bin/env bash
set -euo pipefail
python3 scripts/bootstrap/render_scanner_profile.py spot paper config/scanner/runtime/spot.paper.json
python3 scripts/bootstrap/render_scanner_profile.py spot prod config/scanner/runtime/spot.prod.json
python3 scripts/bootstrap/render_scanner_profile.py futures paper config/scanner/runtime/futures.paper.json
python3 scripts/bootstrap/render_scanner_profile.py futures prod config/scanner/runtime/futures.prod.json
