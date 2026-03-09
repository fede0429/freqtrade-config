#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import json

from services.scanner.live_health import evaluate_live_scanner_health


def _render_md(payload: dict) -> str:
    lines = [
        '# Live Scanner Cutover Validation',
        '',
        f"- Profile: `{payload['profile_name']}`",
        f"- Market: `{payload['market']}`",
        f"- Exchange: `{payload['exchange_name']}`",
        f"- Source mode: `{payload['source_mode']}`",
        f"- CCXT installed: `{payload['ccxt_installed']}`",
        f"- Trading config exists: `{payload['trading_config_exists']}`",
        f"- Universe count: `{payload['universe_count']}`",
        f"- Live probe attempted: `{payload['live_probe_attempted']}`",
        f"- Live probe ok: `{payload['live_probe_ok']}`",
        f"- Probe L1 env: `{payload['probe_level_1_env']}`",
        f"- Probe L2 markets: `{payload['probe_level_2_markets']}`",
        f"- Probe L3 ohlcv: `{payload['probe_level_3_ohlcv']}`",
        f"- Probe success/fail: `{payload['probe_fetch_success_count']}/{payload['probe_fetch_fail_count']}`",
        f"- Probe avg latency ms: `{payload['probe_avg_latency_ms']}`",
        '',
        '## Candidate pairs',
        '',
    ]
    lines.extend([f'- `{pair}`' for pair in payload['candidate_pairs']])
    lines.extend(['', '## Probe symbols tested', ''])
    lines.extend([f'- `{pair}`' for pair in payload.get('probe_symbols_tested', [])] or ['- none'])
    lines.extend(['', '## Probe error types', ''])
    lines.extend([f'- `{item}`' for item in payload.get('probe_error_types', [])] or ['- none'])
    lines.extend(['', '## Issues', ''])
    if payload['issues']:
        lines.extend([f'- {item}' for item in payload['issues']])
    else:
        lines.append('- none')
    lines.extend(['', '## Recommendations', ''])
    lines.extend([f'- {item}' for item in payload['recommendations']])
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True)
    parser.add_argument('--probe-live', action='store_true')
    parser.add_argument('--output-json', required=True)
    parser.add_argument('--output-md', required=True)
    args = parser.parse_args()

    health = evaluate_live_scanner_health(args.profile, probe_live=args.probe_live).to_dict()
    profile_name = Path(args.profile).name
    if 'scanner-live' not in profile_name and not profile_name.endswith('.live.json'):
        health['issues'].append(f'profile filename is not explicit enough for live cutover: {profile_name}')
        health['recommendations'].append('Prefer runtime profiles named like spot.paper.scanner-live.json to avoid operator mistakes.')
    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(health, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    out_md.write_text(_render_md(health), encoding='utf-8')
    print(json.dumps({'issues': len(health['issues']), 'profile': health['profile_name']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
