#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from services.execution.startup_gate import StartupGate
from services.execution.release_loader import load_json


def _load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        data[key.strip()] = value.strip()
    return data


def _api_credentials(bundle, root: Path) -> tuple[str, str] | None:
    if not bundle.compose_env_file:
        return None
    env_values = _load_env_file(root / bundle.compose_env_file)
    prefix = 'SPOT' if bundle.market_type == 'spot' else 'FUTURES'
    username = env_values.get(f'{prefix}_API_USERNAME')
    password = env_values.get(f'{prefix}_API_PASSWORD')
    if not username or not password:
        return None
    return username, password


def _wait_for_api(bundle, root: Path, timeout_seconds: int = 90) -> str | None:
    trading_config = load_json(root / bundle.trading_config)
    api_server = trading_config.get('api_server', {})
    if not api_server.get('enabled', False):
        return None

    listen_port = int(api_server.get('listen_port', 8080))
    credentials = _api_credentials(bundle, root)
    if not credentials:
        return None

    username, password = credentials
    token = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')
    headers = {'Authorization': f'Basic {token}'}
    show_config_url = f'http://127.0.0.1:{listen_port}/api/v1/show_config'

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        request = urllib.request.Request(show_config_url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 200:
                    return show_config_url.rsplit('/', 1)[0]
        except urllib.error.URLError:
            time.sleep(2)
            continue
        time.sleep(2)
    return None


def _start_trader_via_api(api_base_url: str, bundle, root: Path) -> bool:
    credentials = _api_credentials(bundle, root)
    if not credentials:
        return False
    username, password = credentials
    token = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json',
    }
    request = urllib.request.Request(f'{api_base_url}/start', data=b'{}', headers=headers, method='POST')
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status == 200


def main() -> int:
    parser = argparse.ArgumentParser(description='Run preflight and arm trader startup only if checks pass.')
    parser.add_argument('release_profile', help='Path to release runtime profile JSON')
    parser.add_argument('--execute', action='store_true', help='Actually run docker compose up after preflight passes')
    parser.add_argument('--allow-hold', action='store_true', help='Still emit startup bundle even if startup is blocked')
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    profile_path = Path(args.release_profile)
    if not profile_path.is_absolute():
        profile_path = (root / profile_path).resolve()

    gate = StartupGate(profile_path)
    decision, preflight_path = gate.run_preflight()
    approved = bool(decision.get('approved', False))

    bundle = gate.build_bundle(preflight_path=preflight_path, approved=approved)
    bundle_path = gate.write_bundle(bundle)

    print(json.dumps({
        'preflight_report': str(preflight_path.relative_to(root)) if preflight_path.is_relative_to(root) else str(preflight_path),
        'startup_bundle': str(bundle_path.relative_to(root)) if bundle_path.is_relative_to(root) else str(bundle_path),
        'approved': approved,
        'startup_mode': bundle.startup_mode,
        'command_preview': bundle.command_preview,
        'compose_env_file': bundle.compose_env_file,
    }, indent=2, ensure_ascii=False))

    if not approved:
        if args.allow_hold:
            return 0
        return 2

    if args.execute:
        result = subprocess.run(bundle.command_preview, cwd=root)
        if result.returncode != 0:
            return int(result.returncode)

        api_base_url = _wait_for_api(bundle, root)
        if api_base_url:
            try:
                started = _start_trader_via_api(api_base_url, bundle, root)
                print(json.dumps({
                    'api_base_url': api_base_url,
                    'api_start_issued': started,
                }, ensure_ascii=False))
            except urllib.error.URLError as exc:
                print(json.dumps({
                    'api_base_url': api_base_url,
                    'api_start_issued': False,
                    'warning': f'API start failed: {exc}',
                }, ensure_ascii=False))
        return 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
