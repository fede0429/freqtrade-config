#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution.pipeline_trace import backfill_trace_columns, ensure_trace_columns, trace_coverage


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Migrate signal pipeline db to include trace columns and uniqueness/index constraints.')
    p.add_argument('--signal-pipeline-db', required=True)
    p.add_argument('--as-of-date', default=None)
    p.add_argument('--output-json', default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.signal_pipeline_db)
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    result = {
        'migration': ensure_trace_columns(db_path),
        'backfill': backfill_trace_columns(db_path),
        'coverage': trace_coverage(db_path, args.as_of_date),
    }
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
