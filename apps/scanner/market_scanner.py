#!/usr/bin/env python3
"""Market scanner v4.

标准化输出四类结果：
- tradable_pairs
- market_regime
- risk_flags
- ranking_scores

运行模式：
1. --source mock: 使用内置样本
2. --source fixture: 使用本地 fixture / OHLCV 样本
3. --source live: 使用 ccxt 从交易所抓取
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from services.scanner import ScanSnapshot, classify_market_regime, evaluate_pair, load_scanner_profile
from services.scanner.market_data import MarketDataError, load_fixture_metrics, load_live_metrics


MOCK_PAIRS: List[Dict[str, Any]] = [
    {"pair": "BTC/USDT", "liquidity_usd": 18000000, "volume_ratio": 1.35, "momentum_24h": 2.4, "momentum_1h": 0.6, "volatility": 4.1},
    {"pair": "ETH/USDT", "liquidity_usd": 12000000, "volume_ratio": 1.22, "momentum_24h": 1.3, "momentum_1h": 0.3, "volatility": 4.8},
    {"pair": "SOL/USDT", "liquidity_usd": 7200000, "volume_ratio": 1.5, "momentum_24h": 4.2, "momentum_1h": 1.0, "volatility": 6.2},
    {"pair": "XRP/USDT", "liquidity_usd": 6500000, "volume_ratio": 1.1, "momentum_24h": -0.6, "momentum_1h": -0.1, "volatility": 3.5},
    {"pair": "DOGE/USDT", "liquidity_usd": 2900000, "volume_ratio": 1.18, "momentum_24h": 0.8, "momentum_1h": 0.2, "volatility": 8.6},
    {"pair": "AVAX/USDT", "liquidity_usd": 1600000, "volume_ratio": 0.92, "momentum_24h": -6.4, "momentum_1h": -1.2, "volatility": 10.4},
]


def build_snapshot(profile: Dict[str, Any], pair_metrics: List[Dict[str, Any]], source_mode: str) -> ScanSnapshot:
    rankings = []
    decisions = []
    aggregated_flags = set()

    for item in pair_metrics[: profile['selection']['top_n']]:
        ranking, decision = evaluate_pair(item, profile)
        rankings.append(ranking)
        decisions.append(decision)
        aggregated_flags.update(ranking.risk_flags)

    rankings.sort(key=lambda item: item.score, reverse=True)
    tradable_pairs = [item.pair for item in rankings if item.tradable]
    regime = classify_market_regime(rankings, profile)
    if regime.market_pressure == 'block':
        aggregated_flags.add('market_pressure_block')
    elif regime.market_pressure == 'reduce_only':
        aggregated_flags.add('market_reduce_only')

    return ScanSnapshot(
        scan_timestamp=datetime.now(timezone.utc).isoformat(),
        profile_name=profile['profile_name'],
        market=profile['market'],
        tradable_pairs=tradable_pairs,
        market_regime=regime,
        risk_flags=sorted(aggregated_flags),
        ranking_scores=rankings,
        pair_decisions=decisions,
        metadata={
            'selection_top_n': profile['selection']['top_n'],
            'selected_count': len(tradable_pairs),
            'source_mode': source_mode,
            'candidate_count': len(pair_metrics),
        },
    )


def _load_exchange_config(root: Path, profile: Dict[str, Any]) -> Dict[str, Any]:
    source = profile.get('source', {})
    trading_config_rel = source.get('trading_config')
    if not trading_config_rel:
        return {}
    trading_cfg_path = root / trading_config_rel
    if not trading_cfg_path.exists():
        raise SystemExit(f'trading config not found: {trading_cfg_path}')
    payload = json.loads(trading_cfg_path.read_text(encoding='utf-8'))
    return payload.get('exchange', {})


def _resolve_source(profile: Dict[str, Any], args: argparse.Namespace) -> Tuple[str, List[Dict[str, Any]]]:
    source_mode = args.source or profile.get('source', {}).get('default_mode', 'mock')
    if source_mode == 'mock':
        return source_mode, MOCK_PAIRS
    if source_mode == 'fixture':
        fixture_path = args.fixture or profile.get('source', {}).get('fixture_path')
        if not fixture_path:
            raise SystemExit('fixture mode requires --fixture or source.fixture_path')
        return source_mode, load_fixture_metrics(fixture_path)
    if source_mode == 'live':
        root = Path(__file__).resolve().parents[2]
        exchange_cfg = _load_exchange_config(root, profile)
        return source_mode, load_live_metrics(exchange_cfg, profile)
    raise SystemExit(f'unsupported source mode: {source_mode}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True, help='scanner profile json path')
    parser.add_argument('--output', help='output path for snapshot json')
    parser.add_argument('--mock', action='store_true', help='backward-compatible alias for --source mock')
    parser.add_argument('--source', choices=['mock', 'fixture', 'live'], help='market data source mode')
    parser.add_argument('--fixture', help='path to fixture metrics or OHLCV json')
    args = parser.parse_args()

    profile = load_scanner_profile(args.profile)
    if args.mock and not args.source:
        args.source = 'mock'

    try:
        source_mode, pair_metrics = _resolve_source(profile, args)
        snapshot = build_snapshot(profile, pair_metrics, source_mode)
    except MarketDataError as exc:
        raise SystemExit(str(exc)) from exc

    payload = snapshot.to_dict()
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + '\n', encoding='utf-8')
    else:
        print(rendered)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
