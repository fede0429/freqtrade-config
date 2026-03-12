def compare_pair_rows(baseline, current):
    return {
        "confidence_baseline": baseline.get("confidence"),
        "confidence_current": current.get("confidence"),
        "confidence_delta": round(float(current.get("confidence", 0.0)) - float(baseline.get("confidence", 0.0)), 4),
        "governance_gate_baseline": baseline.get("governance_gate"),
        "governance_gate_current": current.get("governance_gate"),
        "trading_mode_baseline": baseline.get("trading_mode"),
        "trading_mode_current": current.get("trading_mode"),
        "entry_allowed_baseline": baseline.get("entry_allowed"),
        "entry_allowed_current": current.get("entry_allowed"),
        "stake_multiplier_baseline": baseline.get("stake_multiplier"),
        "stake_multiplier_current": current.get("stake_multiplier"),
        "target_rr_baseline": baseline.get("target_rr"),
        "target_rr_current": current.get("target_rr"),
        "news_governance_baseline": baseline.get("news_governance"),
        "news_governance_current": current.get("news_governance"),
    }
