import json
from pathlib import Path

def load_calibration_config(path="user_data/config/calibration_config.json"):
    p = Path(path)
    if not p.exists():
        return {"entry_confidence_grid":[0.70,0.75,0.80],"news_min_credibility_grid":[0.60,0.70,0.80],"stake_multiplier_caps":[1.0,1.15,1.30],"mode":"shadow"}
    return json.loads(p.read_text(encoding="utf-8"))
