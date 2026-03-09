#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: generate_release_checklist.py <preflight.json>')
        return 1
    preflight_path = Path(sys.argv[1]).resolve()
    data = json.loads(preflight_path.read_text(encoding='utf-8'))
    lines = [
        f"# Release Checklist - {data['market_type']} / {data['environment']}",
        "",
        f"- Release mode: {data['mode']}",
        f"- Approved: {data['approved']}",
        f"- Channel: {data['release_channel']}",
        "",
        "## Preflight Checks",
    ]
    for item in data['checks']:
        lines.append(f"- [{item['status']}] {item['name']}: {item['detail']}")
    lines.extend(["", "## Required Actions"])
    for item in data['required_actions']:
        lines.append(f"- {item}")
    out = preflight_path.with_suffix('.md')
    out.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print(out)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
