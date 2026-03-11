#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROME_TZ = ZoneInfo("Europe/Rome")
LOG_TIMESTAMP_RE = re.compile(r"^(?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}\s+-")


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_api_json(port: int, username: str, password: str, endpoint: str) -> dict[str, Any] | list[Any]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/v1/{endpoint}",
        headers={"Authorization": f"Basic {token}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def parse_log_timestamp(line: str) -> datetime | None:
    match = LOG_TIMESTAMP_RE.match(line)
    if not match:
        return None
    return datetime.strptime(match.group("stamp"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def iso_utc(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


def iso_rome(value: datetime | None) -> str | None:
    return value.astimezone(ROME_TZ).isoformat() if value else None


def tail_lines(path: Path, limit: int = 200) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]


def last_heartbeat_timestamp(lines: list[str]) -> datetime | None:
    for line in reversed(lines):
        if "Bot heartbeat" in line:
            parsed = parse_log_timestamp(line)
            if parsed:
                return parsed
    for line in reversed(lines):
        parsed = parse_log_timestamp(line)
        if parsed:
            return parsed
    return None


def recent_real_errors(lines: list[str]) -> list[str]:
    results: list[str] = []
    for line in lines:
        lower = line.lower()
        if "traceback" in lower or "exception:" in lower or " - critical - " in lower:
            results.append(line)
            continue
        if " - error - " in lower and "task was destroyed but it is pending" not in lower:
            results.append(line)
    return results[-6:]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def bot_payload(
    *,
    key: str,
    label: str,
    market_type: str,
    port: int,
    username: str,
    password: str,
    trading_config_path: Path,
    scanner_path: Path,
    report_path: Path,
    preflight_path: Path,
    log_path: Path,
) -> dict[str, Any]:
    trading_config = load_json(trading_config_path)
    scanner = load_json(scanner_path)
    report = load_json(report_path)
    preflight = load_json(preflight_path)
    show_config = fetch_api_json(port, username, password, "show_config")
    balance = fetch_api_json(port, username, password, "balance")
    profit = fetch_api_json(port, username, password, "profit")
    status = fetch_api_json(port, username, password, "status")

    lines = tail_lines(log_path)
    heartbeat = last_heartbeat_timestamp(lines)
    issues: list[str] = []

    state = str(show_config.get("state", "unknown")).lower()
    if state != "running":
        issues.append(f"bot_state={state}")

    if scanner.get("metadata", {}).get("source_mode") != "live":
        issues.append(f"scanner_source={scanner.get('metadata', {}).get('source_mode')}")

    if report.get("risk", {}).get("guard_status") != "healthy":
        issues.append(f"guard_status={report.get('risk', {}).get('guard_status')}")

    if not preflight.get("approved", False):
        issues.append("preflight_blocked")

    issues.extend(recent_real_errors(lines))

    total_wallet = safe_float(balance.get("total"))
    allocated_wallet = safe_float(balance.get("starting_capital"))
    tradable_ratio = safe_float(trading_config.get("tradable_balance_ratio"), 1.0)
    profit_all = safe_float(profit.get("profit_all_fiat"))
    current_drawdown = safe_float(profit.get("current_drawdown"))
    trade_count = int(profit.get("trade_count", 0) or 0)
    closed_trade_count = int(profit.get("closed_trade_count", 0) or 0)
    open_positions = len(status) if isinstance(status, list) else 0

    return {
        "key": key,
        "label": label,
        "market_type": market_type,
        "state": state,
        "dry_run": bool(show_config.get("dry_run", False)),
        "strategy": show_config.get("strategy"),
        "timeframe": show_config.get("timeframe"),
        "trading_mode": show_config.get("trading_mode"),
        "margin_mode": show_config.get("margin_mode") or "spot",
        "short_allowed": bool(show_config.get("short_allowed", False)),
        "dry_run_wallet_usd": safe_float(trading_config.get("dry_run_wallet")),
        "wallet_total_usd": total_wallet,
        "wallet_allocated_usd": allocated_wallet,
        "tradable_balance_ratio": tradable_ratio,
        "wallet_unallocated_usd": round(max(total_wallet - allocated_wallet, 0.0), 4),
        "net_pnl_usd": profit_all,
        "open_positions": open_positions,
        "trade_count": trade_count,
        "closed_trade_count": closed_trade_count,
        "winrate": safe_float(profit.get("winrate")),
        "profit_factor": profit.get("profit_factor"),
        "current_drawdown_ratio": current_drawdown,
        "scanner_source_mode": scanner.get("metadata", {}).get("source_mode"),
        "scanner_selected_count": int(scanner.get("metadata", {}).get("selected_count", 0) or 0),
        "scanner_candidate_count": int(scanner.get("metadata", {}).get("candidate_count", 0) or 0),
        "guard_status": report.get("risk", {}).get("guard_status"),
        "preflight_approved": bool(preflight.get("approved", False)),
        "top_pairs": list(scanner.get("tradable_pairs", []))[:6],
        "waiting_for_first_trade": state == "running" and trade_count == 0,
        "last_heartbeat_utc": iso_utc(heartbeat),
        "last_heartbeat_rome": iso_rome(heartbeat),
        "issues": issues,
    }


def build_dashboard(root: Path, env_path: Path) -> dict[str, Any]:
    env = load_env_file(env_path)
    now_utc = datetime.now(UTC)

    spot = bot_payload(
        key="spot",
        label="Spot Paper",
        market_type="spot",
        port=8080,
        username=env.get("SPOT_API_USERNAME", "paper_admin"),
        password=env.get("SPOT_API_PASSWORD", ""),
        trading_config_path=root / "config/runtime/spot.paper.dynamic.json",
        scanner_path=root / "reports/scanner/latest_scan.json",
        report_path=root / "reports/operations/daily/studio_daily_report_spot_paper_latest.json",
        preflight_path=root / "reports/deploy/preflight_spot_paper.json",
        log_path=root / "logs/spot/freqtrade_spot.log",
    )
    futures = bot_payload(
        key="futures",
        label="Futures Paper",
        market_type="futures",
        port=8081,
        username=env.get("FUTURES_API_USERNAME", "futures_admin"),
        password=env.get("FUTURES_API_PASSWORD", ""),
        trading_config_path=root / "config/runtime/futures.paper.dynamic.json",
        scanner_path=root / "reports/scanner/latest_scan_futures_paper.json",
        report_path=root / "reports/operations/daily/studio_daily_report_futures_paper_latest.json",
        preflight_path=root / "reports/deploy/preflight_futures_paper.json",
        log_path=root / "logs/futures/freqtrade_futures.log",
    )

    bots = [spot, futures]
    all_running = all(bot["state"] == "running" for bot in bots)
    guards_healthy = all(bot["guard_status"] == "healthy" for bot in bots)
    preflight_ok = all(bot["preflight_approved"] for bot in bots)
    any_trades = any(bot["trade_count"] > 0 for bot in bots)

    overall_status = "healthy"
    if not (all_running and guards_healthy and preflight_ok):
        overall_status = "attention"
    elif not any_trades:
        overall_status = "observing"

    return {
        "generated_at_utc": iso_utc(now_utc),
        "generated_at_rome": iso_rome(now_utc),
        "server_timezone": os.environ.get("TZ", "Etc/UTC"),
        "log_timezone_note": "Server and bot logs are currently emitted in UTC, not Europe/Rome.",
        "overall_status": overall_status,
        "summary": {
            "bots_running": sum(1 for bot in bots if bot["state"] == "running"),
            "total_bots": len(bots),
            "total_wallet_usd": round(sum(bot["wallet_total_usd"] for bot in bots), 2),
            "total_allocated_usd": round(sum(bot["wallet_allocated_usd"] for bot in bots), 2),
            "total_trades": sum(bot["trade_count"] for bot in bots),
            "total_open_positions": sum(bot["open_positions"] for bot in bots),
            "all_preflight_approved": preflight_ok,
            "all_guards_healthy": guards_healthy,
        },
        "bots": bots,
    }


def write_output(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a combined validation dashboard payload for spot/futures paper bots.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--env-file", default="config/secrets/.env", help="Env file path relative to repo root.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    env_path = Path(args.env_file)
    if not env_path.is_absolute():
        env_path = (root / env_path).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (root / output_path).resolve()
    payload = build_dashboard(root, env_path)
    write_output(payload, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())