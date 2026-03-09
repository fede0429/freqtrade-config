#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple

sys.path.insert(0, '/freqtrade')

from freqtrade.exchange.exchange import Exchange
from freqtrade.configuration import Configuration
from freqtrade.enums import CandleType
import pandas as pd
import numpy as np

def analyze_trend(df: pd.DataFrame) -> str:
    if len(df) < 200:
        return 'UNKNOWN'
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()
    last = df.iloc[-1]
    if last['ema50'] > last['ema200'] * 1.02:
        return 'BULL'
    elif last['ema50'] < last['ema200'] * 0.98:
        return 'BEAR'
    return 'RANGE'

def calc_momentum(df: pd.DataFrame, period: int) -> float:
    if len(df) < period + 1:
        return 0.0
    old_price = df['close'].iloc[-(period+1)]
    new_price = df['close'].iloc[-1]
    return ((new_price - old_price) / old_price) * 100

def calc_atr_pct(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period + 1:
        return 0.0
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean().iloc[-1]
    return (atr / df['close'].iloc[-1]) * 100

def calc_risk_score(df: pd.DataFrame, ticker_24h: Dict) -> float:
    mom_24h = ticker_24h.get('percentage', 0)
    trend = analyze_trend(df)
    trend_score = 1.0 if trend == 'BULL' and mom_24h > 0 else 0.5
    mom_score = min(abs(mom_24h) / 20.0, 1.0)
    return trend_score + mom_score

def scan_market(config_path: str = '/freqtrade/user_data/config.json'):
    config = Configuration.from_files([config_path])
    config['exchange']['key'] = ''
    config['exchange']['secret'] = ''
    config['dry_run'] = True
    exchange = Exchange(config, validate=False)
    tickers = exchange.get_tickers()
    usdt_pairs = {p: t for p, t in tickers.items() if p.endswith('/USDT') and not any(x in p for x in ['USD1/USDT', 'USDC/USDT', 'BUSD/USDT', 'USDT/USDT', 'DOWN/USDT', 'UP/USDT', 'BEAR/USDT', 'BULL/USDT'])}
    min_volume = 5_000_000
    liquid_pairs = {}
    for p, t in usdt_pairs.items():
        try:
            vol = float(t.get('quoteVolume', 0))
            if vol >= min_volume:
                liquid_pairs[p] = t
        except:
            continue
    scored = []
    for pair, ticker in liquid_pairs.items():
        try:
            volume = float(ticker.get('quoteVolume', 0))
            pct = float(ticker.get('percentage', 0))
            score = (volume / 1e9) * (1 + abs(pct) / 100)
            scored.append((pair, score, volume, pct))
        except:
            continue
    scored.sort(key=lambda x: x[1], reverse=True)
    top_pairs = scored[:20] if len(scored) >= 20 else scored[:8]
    results = []
    high_risk_signals = []
    
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=6)).timestamp() * 1000)
    
    for pair, score, volume, pct24 in top_pairs[:8]:
        try:
            ohlcv = exchange.get_historic_ohlcv(pair, timeframe='15m', since_ms=since_ms, candle_type=CandleType.SPOT)
            if ohlcv is None or len(ohlcv) < 50:
                results.append({'pair': pair.split('/')[0], 'trend': 'UNKNOWN', 'risk_score': round(min(abs(pct24) / 20.0, 1.0), 3), 'mom_24h': round(pct24, 2), 'mom_4h': 0.0, 'atr_pct': 0.0})
                continue
            ohlcv_df = pd.DataFrame(ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
            trend = analyze_trend(ohlcv_df)
            mom_4h = calc_momentum(ohlcv_df, 16)
            atr_pct = calc_atr_pct(ohlcv_df)
            risk_score = calc_risk_score(ohlcv_df, {'percentage': pct24})
            result = {'pair': pair.split('/')[0], 'trend': trend, 'risk_score': round(risk_score, 3), 'mom_24h': round(pct24, 2), 'mom_4h': round(mom_4h, 2), 'atr_pct': round(atr_pct, 2)}
            results.append(result)
            if risk_score >= 0.82 and abs(pct24) >= 8 and abs(mom_4h) >= 2 and trend == 'BULL':
                leverage = 1 if abs(pct24) > 20 else 2
                high_risk_signals.append({'pair': pair.split('/')[0], 'risk_score': risk_score, 'mom_24h': pct24, 'mom_4h': mom_4h, 'atr_pct': atr_pct, 'trend': trend, 'suggested_leverage': f'1x（上限{leverage+1}x）'})
        except:
            results.append({'pair': pair.split('/')[0], 'trend': 'UNKNOWN', 'risk_score': round(min(abs(pct24) / 20.0, 1.0), 3), 'mom_24h': round(pct24, 2), 'mom_4h': 0.0, 'atr_pct': 0.0})
            continue
    trends = [r['trend'] for r in results]
    regime = 'risk_on' if trends.count('BULL') >= 6 else 'risk_off' if trends.count('BEAR') >= 6 else 'mixed' if trends.count('BULL') >= 3 else 'rotation/range'
    output = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'timezone': 'Europe/Rome', 'market_regime': regime, 'bull_count': trends.count('BULL'), 'bear_count': trends.count('BEAR'), 'range_count': trends.count('RANGE'), 'top_pairs': results, 'wait_confirm_signals': high_risk_signals, 'triggered': len(high_risk_signals) > 0}
    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    scan_market()
