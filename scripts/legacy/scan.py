import ccxt
import time

exchange = ccxt.binance({'enableRateLimit': True})
exchange.load_markets()

pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
print("Scanning:", pairs)

results = []
for p in pairs:
    try:
        ticker = exchange.fetch_ticker(p)
        change = ticker.get('percentage', 0)
        vol = ticker.get('quoteVolume', 0)
        results.append({"pair": p, "change": change, "vol": vol})
    except Exception as e:
        print(f"Error {p}: {e}")
        
results.sort(key=lambda x: x['vol'], reverse=True)

for r in results:
    print(f"{r['pair']} - Change: {r['change']}% - Vol: {r['vol']}")

# Detect high-risk signal (arbitrary condition for script e.g., > 5% change)
high_risk = [r for r in results if r['change'] is not None and abs(r['change']) > 3]

if high_risk:
    print("HIGH_RISK_SIGNAL:" + str(high_risk[0]))
