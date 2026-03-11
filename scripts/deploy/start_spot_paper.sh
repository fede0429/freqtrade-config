#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
PYTHONPATH=. python3 scripts/deploy/start_trader.py config/release/runtime/spot.paper.json "$@"
