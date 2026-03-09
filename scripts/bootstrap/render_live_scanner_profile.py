#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('base_profile')
    parser.add_argument('output_profile')
    args = parser.parse_args()

    src = Path(args.base_profile)
    dst = Path(args.output_profile)
    payload = json.loads(src.read_text(encoding='utf-8'))
    payload.setdefault('source', {})['default_mode'] = 'live'
    payload['source'].pop('fixture_path', None)
    payload['source']['profile_variant'] = 'scanner-live'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'wrote {dst}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
