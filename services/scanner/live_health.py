from __future__ import annotations

import importlib.util
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List

from services.scanner.market_data import compute_metrics_from_ohlcv, resolve_candidate_pairs


@dataclass
class LiveScannerHealth:
    profile_name: str
    market: str
    exchange_name: str
    source_mode: str
    ccxt_installed: bool
    trading_config_exists: bool
    runtime_profile_exists: bool
    candidate_pairs: List[str]
    universe_count: int
    live_probe_attempted: bool
    live_probe_ok: bool
    probe_level_1_env: str
    probe_level_2_markets: str
    probe_level_3_ohlcv: str
    probe_symbols_tested: List[str]
    probe_fetch_success_count: int
    probe_fetch_fail_count: int
    probe_avg_latency_ms: float | None
    probe_error_types: List[str]
    issues: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _classify_exc(exc: Exception) -> str:
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    if 'rate limit' in text or 'ddos' in name or 'ratelimit' in name:
        return 'rate_limit_error'
    if 'network' in text or 'timeout' in text or 'request' in name:
        return 'network_error'
    if 'symbol' in text or 'market' in text:
        return 'symbol_mapping_error'
    return 'probe_error'


def evaluate_live_scanner_health(profile_path: str | Path, probe_live: bool = False) -> LiveScannerHealth:
    profile_path = Path(profile_path)
    runtime_profile_exists = profile_path.exists()
    if not runtime_profile_exists:
        raise FileNotFoundError(profile_path)

    profile = _load_json(profile_path)
    root = profile_path.parents[3]
    source = profile.get('source', {})
    trading_rel = source.get('trading_config', '')
    trading_path = root / trading_rel if trading_rel else root / 'missing.json'
    trading_exists = trading_path.exists()
    trading_cfg = _load_json(trading_path) if trading_exists else {}
    exchange_cfg = trading_cfg.get('exchange', {})
    exchange_name = exchange_cfg.get('name', 'binance')

    ccxt_installed = importlib.util.find_spec('ccxt') is not None
    candidate_pairs = resolve_candidate_pairs(exchange_cfg, profile)
    issues: List[str] = []
    recommendations: List[str] = []
    probe_error_types: List[str] = []
    probe_symbols_tested: List[str] = []
    probe_fetch_success_count = 0
    probe_fetch_fail_count = 0
    probe_avg_latency_ms: float | None = None

    source_mode = source.get('default_mode', 'fixture')
    probe_level_1_env = 'ready'
    probe_level_2_markets = 'not_run'
    probe_level_3_ohlcv = 'not_run'

    if source_mode != 'live':
        issues.append(f'source.default_mode is {source_mode}, not live')
        recommendations.append('Switch scanner runtime profile to source.default_mode=live before cutover.')
        probe_level_1_env = 'blocked'

    if not trading_exists:
        issues.append(f'trading config missing: {trading_path}')
        recommendations.append('Render trading runtime config before live scanner cutover.')
        probe_level_1_env = 'blocked'

    if not ccxt_installed:
        issues.append('ccxt is not installed in current environment')
        recommendations.append('Install ccxt on the deployment machine before enabling live scanner.')
        probe_level_1_env = 'blocked'

    if len(candidate_pairs) < 3:
        issues.append('candidate pair universe too small')
        recommendations.append('Expand source.universe.pairs or quote-asset market discovery.')

    live_probe_ok = False
    if probe_live and ccxt_installed and trading_exists and source_mode == 'live':
        try:
            import ccxt  # type: ignore

            exchange_cls = getattr(ccxt, exchange_name, None)
            if exchange_cls is None:
                issues.append(f'ccxt exchange class not found: {exchange_name}')
                probe_level_2_markets = 'blocked'
            else:
                exchange = exchange_cls(dict(exchange_cfg.get('ccxt_config', {})))
                try:
                    markets = exchange.load_markets()
                    probe_level_2_markets = 'ready'
                    latencies = []
                    for pair in candidate_pairs[:3]:
                        probe_symbols_tested.append(pair)
                        if pair not in markets:
                            issues.append(f'pair unavailable on live exchange: {pair}')
                            probe_error_types.append('symbol_mapping_error')
                            probe_fetch_fail_count += 1
                            continue
                        started = time.perf_counter()
                        try:
                            candles = exchange.fetch_ohlcv(pair, timeframe=source.get('timeframe', '1h'), limit=int(source.get('lookback_candles', 72)))
                            latency_ms = (time.perf_counter() - started) * 1000.0
                            latencies.append(latency_ms)
                            if not candles:
                                issues.append(f'empty OHLCV response: {pair}')
                                probe_error_types.append('empty_ohlcv_error')
                                probe_fetch_fail_count += 1
                                continue
                            if len(candles) < 25:
                                issues.append(f'short OHLCV response: {pair} -> {len(candles)} candles')
                                probe_error_types.append('short_ohlcv_error')
                                probe_fetch_fail_count += 1
                                continue
                            compute_metrics_from_ohlcv(pair, candles)
                            probe_fetch_success_count += 1
                        except Exception as exc:  # pragma: no cover
                            issues.append(f'ohlcv probe failed for {pair}: {exc}')
                            probe_error_types.append(_classify_exc(exc))
                            probe_fetch_fail_count += 1
                    if latencies:
                        probe_avg_latency_ms = round(sum(latencies) / len(latencies), 2)
                    probe_level_3_ohlcv = 'ready' if probe_fetch_success_count > 0 else 'blocked'
                    live_probe_ok = probe_fetch_success_count > 0 and probe_fetch_fail_count == 0
                finally:
                    close = getattr(exchange, 'close', None)
                    if callable(close):
                        close()
        except Exception as exc:  # pragma: no cover
            issues.append(f'live probe failed: {exc}')
            probe_error_types.append(_classify_exc(exc))
            recommendations.append('Validate network egress and exchange reachability on the target host.')
            probe_level_2_markets = 'blocked'
            probe_level_3_ohlcv = 'blocked'
    elif probe_live:
        probe_level_2_markets = 'blocked' if probe_level_1_env == 'blocked' else 'not_run'
        probe_level_3_ohlcv = 'blocked' if probe_level_1_env == 'blocked' else 'not_run'

    if not recommendations and not issues:
        recommendations.append('Live scanner cutover prerequisites look healthy.')

    return LiveScannerHealth(
        profile_name=profile.get('profile_name', 'unknown'),
        market=profile.get('market', 'unknown'),
        exchange_name=exchange_name,
        source_mode=source_mode,
        ccxt_installed=ccxt_installed,
        trading_config_exists=trading_exists,
        runtime_profile_exists=runtime_profile_exists,
        candidate_pairs=candidate_pairs,
        universe_count=len(candidate_pairs),
        live_probe_attempted=probe_live,
        live_probe_ok=live_probe_ok,
        probe_level_1_env=probe_level_1_env,
        probe_level_2_markets=probe_level_2_markets,
        probe_level_3_ohlcv=probe_level_3_ohlcv,
        probe_symbols_tested=probe_symbols_tested,
        probe_fetch_success_count=probe_fetch_success_count,
        probe_fetch_fail_count=probe_fetch_fail_count,
        probe_avg_latency_ms=probe_avg_latency_ms,
        probe_error_types=sorted(set(probe_error_types)),
        issues=issues,
        recommendations=recommendations,
    )
