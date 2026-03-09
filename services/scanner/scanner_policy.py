from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .scanner_types import MarketRegime, PairRanking, ScanDecision


def classify_market_regime(rankings: List[PairRanking], cfg: Dict[str, Any]) -> MarketRegime:
    if not rankings:
        return MarketRegime('unknown', 0.0, 0.0, 'block', ['no candidates'])

    bullish = sum(1 for item in rankings if item.momentum_24h > 0)
    breadth = bullish / len(rankings)
    avg_volatility = sum(item.volatility for item in rankings) / len(rankings)
    max_allowed = cfg['market_regime']['max_volatility_pct']

    if avg_volatility >= max_allowed:
        regime = 'panic'
        pressure = 'block'
        confidence = min(1.0, avg_volatility / max_allowed)
        notes = ['volatility too high']
    elif breadth >= cfg['market_regime']['trend_breadth_threshold']:
        regime = 'trend'
        pressure = 'allow'
        confidence = breadth
        notes = ['breadth supports trend following']
    elif breadth <= cfg['market_regime']['risk_off_breadth_threshold']:
        regime = 'risk_off'
        pressure = 'reduce_only'
        confidence = 1 - breadth
        notes = ['market breadth weak']
    else:
        regime = 'range'
        pressure = 'allow'
        confidence = 0.55
        notes = ['mixed breadth, favor selective entries']
    return MarketRegime(regime, round(confidence, 4), round(breadth, 4), pressure, notes)


def evaluate_pair(pair_metrics: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[PairRanking, ScanDecision]:
    risk_flags: List[str] = []
    reasons: List[str] = []
    score = 0.0

    liquidity = float(pair_metrics.get('liquidity_usd', 0.0))
    vol_ratio = float(pair_metrics.get('volume_ratio', 1.0))
    momentum_24h = float(pair_metrics.get('momentum_24h', 0.0))
    momentum_1h = float(pair_metrics.get('momentum_1h', 0.0))
    volatility = float(pair_metrics.get('volatility', 0.0))

    if liquidity >= cfg['pair_filters']['min_liquidity_usd']:
        score += 25
        reasons.append('liquidity ok')
    else:
        risk_flags.append('low_liquidity')

    if vol_ratio >= cfg['pair_filters']['min_volume_ratio']:
        score += 20
        reasons.append('volume expansion')

    if momentum_24h >= cfg['pair_filters']['min_momentum_24h_pct']:
        score += 20
        reasons.append('24h momentum ok')
    elif momentum_24h <= cfg['pair_filters']['max_drawdown_entry_pct']:
        risk_flags.append('deep_drawdown')

    if momentum_1h >= cfg['pair_filters']['min_momentum_1h_pct']:
        score += 10
        reasons.append('1h momentum ok')

    target_vol = cfg['pair_filters']['target_volatility_pct']
    if volatility <= cfg['pair_filters']['max_volatility_pct']:
        score += max(0.0, 25 - abs(target_vol - volatility) * 4)
        reasons.append('volatility acceptable')
    else:
        risk_flags.append('high_volatility')

    tradable = score >= cfg['selection']['min_score'] and not any(
        flag in cfg['selection']['hard_block_flags'] for flag in risk_flags
    )
    decision = 'allow' if tradable else 'block'
    if not tradable and score >= cfg['selection']['watchlist_min_score']:
        decision = 'watchlist'

    ranking = PairRanking(
        pair=pair_metrics['pair'],
        score=round(score, 2),
        momentum_24h=momentum_24h,
        momentum_1h=momentum_1h,
        volume_ratio=vol_ratio,
        volatility=volatility,
        liquidity_usd=liquidity,
        tradable=tradable,
        risk_flags=risk_flags,
        reasons=reasons,
    )
    scan_decision = ScanDecision(
        pair=pair_metrics['pair'],
        decision=decision,
        score=ranking.score,
        reasons=reasons,
        risk_flags=risk_flags,
    )
    return ranking, scan_decision
