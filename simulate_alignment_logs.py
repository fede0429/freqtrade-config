import sys
import json
import types
from pathlib import Path
from datetime import datetime, timezone

# 1. Improved nested mock helper
def mock_module(name, attributes=None):
    parts = name.split('.')
    for i in range(len(parts)):
        subname = '.'.join(parts[:i+1])
        if subname not in sys.modules:
            m = types.ModuleType(subname)
            sys.modules[subname] = m
    
    m = sys.modules[name]
    if attributes:
        for k, v in attributes.items():
            setattr(m, k, v)
    return m

# Create mocks
mock_module("freqtrade")
mock_module("freqtrade.strategy", {
    "IStrategy": type("IStrategy", (), {"INTERFACE_VERSION": 3}),
    "DecimalParameter": lambda *a, **k: type("P", (), {"value": a[2] if len(a)>2 else 0})(),
    "IntParameter": lambda *a, **k: type("P", (), {"value": a[2] if len(a)>2 else 0})(),
    "BooleanParameter": lambda *a, **k: type("P", (), {"value": a[0] if a else False})(),
    "CategoricalParameter": lambda *a, **k: type("P", (), {"value": a[0][0] if a and a[0] else ""})(),
    "merge_informative_pair": lambda *a, **k: a[0]
})
mock_module("freqtrade.persistence", {"Trade": type("Trade", (), {})})
mock_module("freqtrade.vendor.qtpylib.indicators", {"crossed_below": lambda *a: False})

mock_module("talib.abstract")
mock_module("talib", {
    "abstract": sys.modules["talib.abstract"],
    "EMA": lambda *a, **k: None,
    "RSI": lambda *a, **k: None,
    "ADX": lambda *a, **k: None,
    "ATR": lambda *a, **k: None,
    "PLUS_DI": lambda *a, **k: None,
    "MINUS_DI": lambda *a, **k: None,
    "BBANDS": lambda *a, **k: {"upperband": None, "lowerband": None, "middleband": None},
    "TRANGE": lambda *a, **k: None,
    "STOCHRSI": lambda *a, **k: (None, None)
})

mock_module("numpy", {"nan": float('nan'), "full": lambda *a, **k: [], "isclose": lambda *a, **k: True, "array": lambda *a, **k: [], "nan_to_num": lambda a: a})
mock_module("pandas", {
    "DataFrame": type("DataFrame", (), {}),
    "Series": lambda *a: type("Series", (), {"rolling": lambda *a: type("R", (), {"mean": lambda *a: type("M", (), {"to_numpy": lambda: None})()})()})()
})

# 2. Add current dir to path and import
sys.path.append(str(Path.cwd()))
from user_data.strategies.AgentBridgeStrategy import AgentBridgeStrategy

def simulate():
    strategy = AgentBridgeStrategy()
    
    # Mock some data for the strategy
    strategy._cache = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": "simulation",
        "pairs": {
            "BTC/USDT": {
                "agent_enabled": True,
                "confidence": 0.85,
                "stake_multiplier": 1.2,
                "entry_allowed": True,
                "exit_signal": False,
                "governance_gate": "passed",
                "stoploss_mode": "tighten_only",
                "agent_stoploss": -0.05,
                "target_rr": 3.0
            },
            "ETH/USDT": {
                "agent_enabled": True,
                "confidence": 0.65,
                "stake_multiplier": 1.0,
                "entry_allowed": False,
                "exit_signal": True,
                "exit_reason": "agent_reversal",
                "governance_gate": "passed",
                "stoploss_mode": "tighten_only",
                "agent_stoploss": -0.06,
                "target_rr": 2.5
            }
        }
    }
    strategy._overlay = {
        "shadow_mode": True,
        "enabled_callbacks": {
            "stake": True,
            "exit": True,
            "stoploss": True,
            "roi": True,
            "entry_confirm": True
        },
        "enabled_pairs": ["BTC/USDT", "ETH/USDT"],
        "min_confidence_for_live": 0.72,
        "entry_min_confidence": 0.75,
        "cache_ttl_seconds": 3600
    }

    now = datetime.now(timezone.utc)
    print("Simulating bot_loop_start...")
    strategy.bot_loop_start(now)

    print("Simulating stake decisions...")
    strategy.custom_stake_amount("BTC/USDT", now, 50000.0, 100.0, 10.0, 500.0, 1.0, None, "long")
    strategy.custom_stake_amount("ETH/USDT", now, 3000.0, 100.0, 10.0, 500.0, 1.0, None, "long")

    print("Simulating exit decisions...")
    strategy.custom_exit("BTC/USDT", None, now, 50000.0, 0.02)
    strategy.custom_exit("ETH/USDT", None, now, 3000.0, -0.01)

    print("Simulating stoploss decisions...")
    strategy.custom_stoploss("BTC/USDT", None, now, 50000.0, -0.02, False)
    
    print("Simulating entry confirmation...")
    strategy.confirm_trade_entry("BTC/USDT", "limit", 0.002, 50000.0, "GTC", now, None, "long")
    strategy.confirm_trade_entry("ETH/USDT", "limit", 1.0, 3000.0, "GTC", now, None, "long")

    print("Simulating ROI decisions...")
    strategy.custom_roi("BTC/USDT", None, now, 10, None, "long")

if __name__ == "__main__":
    simulate()
    print("Simulation complete. Logs in user_data/agent_runtime/audit/")
