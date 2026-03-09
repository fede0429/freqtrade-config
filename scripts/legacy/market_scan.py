#!/usr/bin/env python3
"""Market scan: volume, momentum, trend regime for USDT pairs."""
import json, sys, os
from pathlib import Path
from datetime import datetime, timezone

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: pandas/numpy not available")
    sys.exit(1)

DATA_DIR = Path("/freqtrade/user_data/data/binance")
PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT",
         "AVAX_USDT", "DOGE_USDT", "PEPE_USDT", "SUI_USDT", "ZEC_USDT"]

def load_pair(pair, tf):
    fn = DATA_DIR / f"{pair}-{tf}-spot.feather"
    if not fn.exists():
        return None
    df = pd.read_feather(fn)
    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if 'date' in cl or 'time' in cl:
            col_map[c] = 'date'
        elif 'open' in cl:
            col_map[c] = 'open'
        elif 'high' in cl:
            col_map[c] = 'high'
        elif 'low' in cl:
            col_map[c] = 'low'
        elif 'close' in cl:
            col_map[c] = 'close'
        elif 'vol' in cl:
            col_map[c] = 'volume'
    df = df.rename(columns=col_map)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.sort_values('date').reset_index(drop=True)
    return df

def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def rsi(s, n=14):
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/n, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1/n, min_periods=n).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def bb_width(s, n=20):
    ma = s.rolling(n).mean()
    std = s.rolling(n).std()
    return ((ma + 2*std) - (ma - 2*std)) / ma * 100

def macd_signal(s):
    fast = ema(s, 12)
    slow = ema(s, 26)
    macd_line = fast - slow
    sig = ema(macd_line, 9)
    hist = macd_line - sig
    return macd_line.iloc[-1], sig.iloc[-1], hist.iloc[-1]

results = []
for pair in PAIRS:
    df1h = load_pair(pair, "1h")
    df4h = load_pair(pair, "4h")
    if df1h is None or df4h is None:
        continue
    if len(df1h) < 50 or len(df4h) < 20:
        continue
    symbol = pair.replace("_", "/")
    c1 = df1h['close']
    c4 = df4h['close']
    price = c1.iloc[-1]
    vol_24h = df1h['volume'].tail(24).sum() * price
    if len(c1) >= 25:
        chg_24h = (c1.iloc[-1] / c1.iloc[-25] - 1) * 100
    else:
        chg_24h = 0
    chg_7d = (c1.iloc[-1] / c1.iloc[0] - 1) * 100 if len(c1) > 1 else 0
    rsi_1h = rsi(c1, 14).iloc[-1]
    rsi_4h = rsi(c4, 14).iloc[-1]
    ema20 = ema(c1, 20).iloc[-1]
    ema50 = ema(c1, 50).iloc[-1]
    trend_1h = "BULL" if ema20 > ema50 else "BEAR"
    ema20_4h = ema(c4, 20).iloc[-1]
    ema50_4h = ema(c4, 50).iloc[-1] if len(c4) >= 50 else ema(c4, len(c4)).iloc[-1]
    trend_4h = "BULL" if ema20_4h > ema50_4h else "BEAR"
    macd_l, macd_s, macd_h = macd_signal(c1)
    macd_cross = "BULL" if macd_h > 0 else "BEAR"
    bbw = bb_width(c1, 20).iloc[-1]
    squeeze = bbw < 3.0
    tr = pd.concat([
        df1h['high'] - df1h['low'],
        (df1h['high'] - df1h['close'].shift()).abs(),
        (df1h['low'] - df1h['close'].shift()).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.tail(14).mean()
    atr_pct = (atr14 / price) * 100
    vol_6h_avg = df1h['volume'].tail(6).mean()
    vol_24h_avg = df1h['volume'].tail(24).mean()
    vol_surge = vol_6h_avg / vol_24h_avg if vol_24h_avg > 0 else 1.0
    bull_signals = sum([
        trend_1h == "BULL",
        trend_4h == "BULL",
        macd_cross == "BULL",
        rsi_1h > 50,
        rsi_4h > 50
    ])
    if bull_signals >= 4:
        regime = "强多 (Strong Bull)"
    elif bull_signals >= 3:
        regime = "偏多 (Mild Bull)"
    elif bull_signals <= 1:
        regime = "强空 (Strong Bear)"
    else:
        regime = "震荡 (Ranging)"
    high_risk_signal = False
    high_risk_dir = None
    if bull_signals >= 4 and vol_surge > 1.2 and 40 < rsi_1h < 78:
        high_risk_signal = True
        high_risk_dir = "LONG"
    elif bull_signals <= 1 and vol_surge > 1.2 and 22 < rsi_1h < 60:
        high_risk_signal = True
        high_risk_dir = "SHORT"
    results.append({
        "pair": symbol,
        "price": round(price, 6),
        "chg_24h": round(chg_24h, 2),
        "chg_7d": round(chg_7d, 2),
        "vol_24h_usdt": round(vol_24h, 0),
        "rsi_1h": round(rsi_1h, 1),
        "rsi_4h": round(rsi_4h, 1),
        "trend_1h": trend_1h,
        "trend_4h": trend_4h,
        "macd_cross": macd_cross,
        "regime": regime,
        "bb_squeeze": squeeze,
        "atr_pct": round(atr_pct, 3),
        "vol_surge": round(vol_surge, 2),
        "high_risk_signal": high_risk_signal,
        "high_risk_dir": high_risk_dir,
    })

results.sort(key=lambda x: x["vol_24h_usdt"], reverse=True)

print(json.dumps({"scan_time": datetime.now(timezone.utc).isoformat(), "pairs": results}, indent=2))
