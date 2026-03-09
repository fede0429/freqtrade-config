from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class OHLCVWindow:
    pair: str
    closes: List[float]
    volumes: List[float]


class MarketDataError(RuntimeError):
    pass


def _compile_patterns(patterns: Iterable[str]) -> List[re.Pattern[str]]:
    return [re.compile(p) for p in patterns]


def _matches_any(text: str, patterns: List[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def resolve_candidate_pairs(exchange_cfg: Dict[str, Any], scanner_profile: Dict[str, Any]) -> List[str]:
    source = scanner_profile.get('source', {})
    universe = source.get('universe', {})
    explicit = universe.get('pairs') or exchange_cfg.get('pair_whitelist') or []
    if explicit:
        return list(dict.fromkeys(explicit))

    quote = universe.get('quote_asset', 'USDT')
    max_pairs = int(universe.get('max_pairs', 30))
    defaults = [
        f'BTC/{quote}', f'ETH/{quote}', f'SOL/{quote}', f'XRP/{quote}', f'DOGE/{quote}', f'AVAX/{quote}',
        f'LINK/{quote}', f'ADA/{quote}', f'BNB/{quote}', f'TON/{quote}', f'DOT/{quote}', f'NEAR/{quote}',
    ]
    compiled_blacklist = _compile_patterns(exchange_cfg.get('pair_blacklist', []))
    filtered = [p for p in defaults if not _matches_any(p, compiled_blacklist)]
    return filtered[:max_pairs]


def compute_metrics_from_ohlcv(pair: str, candles: List[List[float]]) -> Dict[str, Any]:
    if len(candles) < 25:
        raise MarketDataError(f'{pair}: not enough candles, need >=25 got {len(candles)}')

    closes = [float(row[4]) for row in candles if row and len(row) >= 6]
    volumes = [float(row[5]) for row in candles if row and len(row) >= 6]
    if len(closes) < 25 or len(volumes) < 25:
        raise MarketDataError(f'{pair}: invalid OHLCV rows')

    latest = closes[-1]
    momentum_24h = ((latest / closes[-25]) - 1.0) * 100.0
    momentum_1h = ((latest / closes[-2]) - 1.0) * 100.0
    recent_volume = sum(volumes[-6:])
    baseline_volume = mean(volumes[-24:-6]) if len(volumes[-24:-6]) > 0 else mean(volumes[:-1])
    volume_ratio = (recent_volume / 6.0) / baseline_volume if baseline_volume > 0 else 1.0

    returns: List[float] = []
    for prev, curr in zip(closes[-25:-1], closes[-24:]):
        if prev > 0:
            returns.append(((curr - prev) / prev) * 100.0)
    volatility = math.sqrt(mean([r * r for r in returns])) if returns else 0.0
    liquidity_usd = latest * recent_volume

    return {
        'pair': pair,
        'liquidity_usd': round(liquidity_usd, 2),
        'volume_ratio': round(volume_ratio, 4),
        'momentum_24h': round(momentum_24h, 4),
        'momentum_1h': round(momentum_1h, 4),
        'volatility': round(volatility, 4),
    }


def load_fixture_metrics(path: str | Path) -> List[Dict[str, Any]]:
    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding='utf-8'))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and 'pairs' in payload:
        items = []
        for pair, candles in payload['pairs'].items():
            items.append(compute_metrics_from_ohlcv(pair, candles))
        return items
    raise MarketDataError(f'Unsupported fixture format: {fixture_path}')


def load_live_metrics(exchange_cfg: Dict[str, Any], scanner_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        import ccxt  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on env
        raise MarketDataError('ccxt not installed. Install ccxt before using --source live.') from exc

    source = scanner_profile.get('source', {})
    timeframe = source.get('timeframe', '1h')
    lookback = int(source.get('lookback_candles', 72))
    exchange_name = exchange_cfg.get('name', 'binance')
    exchange_cls = getattr(ccxt, exchange_name, None)
    if exchange_cls is None:
        raise MarketDataError(f'Unsupported exchange for live source: {exchange_name}')

    config = dict(exchange_cfg.get('ccxt_config', {}))
    if exchange_cfg.get('key') and exchange_cfg.get('key') != 'OVERRIDDEN_BY_ENV':
        config['apiKey'] = exchange_cfg['key']
    if exchange_cfg.get('secret') and exchange_cfg.get('secret') != 'OVERRIDDEN_BY_ENV':
        config['secret'] = exchange_cfg['secret']

    exchange = exchange_cls(config)
    try:
        pairs = resolve_candidate_pairs(exchange_cfg, scanner_profile)
        markets = exchange.load_markets()
        compiled_blacklist = _compile_patterns(exchange_cfg.get('pair_blacklist', []))
        metrics: List[Dict[str, Any]] = []
        for pair in pairs:
            if pair not in markets:
                continue
            if _matches_any(pair, compiled_blacklist):
                continue
            candles = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=lookback)
            metrics.append(compute_metrics_from_ohlcv(pair, candles))
        if not metrics:
            raise MarketDataError('No market metrics collected from live exchange.')
        return metrics
    finally:  # pragma: no cover - depends on live network
        close = getattr(exchange, 'close', None)
        if callable(close):
            close()
