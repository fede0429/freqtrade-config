#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.analytics.daily_report_builder import DailyReportBuilder, write_outputs

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Build daily studio operations report')
    p.add_argument('--profile', required=True)
    p.add_argument('--output-dir', default=None)
    return p.parse_args()

def main() -> int:
    args = parse_args()
    profile = json.loads(Path(args.profile).read_text(encoding='utf-8'))
    report = DailyReportBuilder(profile).build()
    out_dir = args.output_dir or profile['paths']['output_dir']
    json_path, md_path = write_outputs(report, out_dir)
    print(f'[OK] wrote {json_path}')
    print(f'[OK] wrote {md_path}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

