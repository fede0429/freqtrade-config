from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from agent_service.aggregator.decision_aggregator import DecisionAggregator
from agent_service.aggregator.provider_health_report import write_provider_health_report
from agent_service.aggregator.observability_report import write_observability_report
from agent_service.aggregator.decision_history_writer import append_decision_history
from agent_service.aggregator.approval_summary_report import write_approval_summary_report
from agent_service.providers.provider_base import ProviderSnapshot, SkillProvider
from agent_service.providers.provider_registry import build_default_provider_registry, build_pair_provider_map

DEFAULT_PAIRS = ["BTC/USDT", "ETH/USDT"]
ROLLOUT_CONFIG_PATH = "user_data/config/provider_rollout.json"
CONFIDENCE_POLICY_PATH = "user_data/config/confidence_policy.json"
EXECUTION_POLICY_PATH = "user_data/config/execution_policy.json"
ANOMALY_POLICY_PATH = "user_data/config/anomaly_policy.json"
COOLDOWN_POLICY_PATH = "user_data/config/cooldown_policy.json"
GOVERNANCE_POLICY_PATH = "user_data/config/governance_policy.json"


def load_json(path: str, default: dict) -> dict:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def load_rollout_config(path: str = ROLLOUT_CONFIG_PATH) -> dict:
    return load_json(path, {
        "enabled_pairs": DEFAULT_PAIRS,
        "provider_defaults": {"tradingview_mcp": True, "dexpaprika": True},
        "required_provider_names": ["tradingview_mcp", "dexpaprika"],
        "rollout_stage": "pair_provider_enablement_v1",
        "pair_provider_overrides": {},
    })


def load_confidence_policy(path: str = CONFIDENCE_POLICY_PATH) -> dict:
    return load_json(path, {
        "global_defaults": {
            "entry_min_confidence": 0.75,
            "max_risk_score": 0.40,
            "neutralize_degraded_provider_score": True,
            "base_live_stake_multiplier": 1.15,
            "trend_high_conf_stake_multiplier": 1.35,
            "base_target_rr": 1.8,
            "trend_target_rr": 2.8,
            "base_agent_stoploss": -0.045,
            "high_conf_agent_stoploss": -0.035,
            "stake_cap_ratio": 0.12,
            "roi_min_trade_duration": 5
        },
        "provider_weights": {"tradingview_mcp": 1.0, "dexpaprika": 1.0},
        "pair_overrides": {}
    })


def load_execution_policy(path: str = EXECUTION_POLICY_PATH) -> dict:
    return load_json(path, {
        "global_defaults": {
            "min_provider_count": 1,
            "fallback_mode": "base_strategy_only",
            "allow_entry_confirm": True,
            "allow_stake": True,
            "allow_exit": True,
            "allow_stoploss": True,
            "allow_roi": True
        },
        "pair_overrides": {}
    })


def load_anomaly_policy(path: str = ANOMALY_POLICY_PATH) -> dict:
    return load_json(path, {
        "global_defaults": {
            "max_provider_latency_ms": 1200,
            "max_score_drift": 0.45,
            "block_on_high_latency": False,
            "block_on_high_drift": True,
            "block_on_risk_flags": ["high_slippage_risk"]
        },
        "pair_overrides": {}
    })


def load_cooldown_policy(path: str = COOLDOWN_POLICY_PATH) -> dict:
    return load_json(path, {
        "global_defaults": {
            "cooldown_minutes_on_blocking_anomaly": 45,
            "cooldown_minutes_on_provider_gate_fail": 20,
            "cooldown_entry_block": True,
            "cooldown_stake_multiplier_cap": 1.0
        },
        "pair_overrides": {}
    })


def load_governance_policy(path: str = GOVERNANCE_POLICY_PATH) -> dict:
    return load_json(path, {
        "global_defaults": {
            "require_provider_gate_passed": True,
            "require_no_blocking_anomaly": True,
            "require_no_active_cooldown": False,
            "default_trading_mode": "shadow_only"
        },
        "pair_overrides": {}
    })


def collect_pair_snapshots(pair_provider_map: Dict[str, List[SkillProvider]]) -> Dict[str, List[ProviderSnapshot]]:
    pair_snapshots: Dict[str, List[ProviderSnapshot]] = {}
    for pair, providers in pair_provider_map.items():
        snapshots: List[ProviderSnapshot] = []
        for provider in providers:
            if provider.kind == "market_data":
                snapshots.append(provider.fetch(pair, {"timeframe": "1h"}))
            else:
                snapshots.append(provider.fetch(pair))
        pair_snapshots[pair] = snapshots
    return pair_snapshots


def write_json_report(payload: dict, output_path: str) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main():
    rollout_config = load_rollout_config()
    confidence_policy = load_confidence_policy()
    execution_policy = load_execution_policy()
    anomaly_policy = load_anomaly_policy()
    cooldown_policy = load_cooldown_policy()
    governance_policy = load_governance_policy()

    providers = build_default_provider_registry()
    write_provider_health_report(providers)
    write_json_report({"confidence_policy": confidence_policy}, "agent_service/reports/confidence_policy_report.json")
    write_json_report({"execution_policy": execution_policy}, "agent_service/reports/execution_policy_report.json")
    write_json_report({"anomaly_policy": anomaly_policy}, "agent_service/reports/anomaly_policy_report.json")
    write_json_report({"cooldown_policy": cooldown_policy}, "agent_service/reports/cooldown_policy_report.json")
    write_json_report({"governance_policy": governance_policy}, "agent_service/reports/governance_policy_report.json")

    pairs = rollout_config.get("enabled_pairs", DEFAULT_PAIRS)
    pair_provider_map = build_pair_provider_map(pairs, rollout_config=rollout_config)
    pair_snapshots = collect_pair_snapshots(pair_provider_map)
    write_observability_report(pair_snapshots)

    aggregator = DecisionAggregator(
        cache_ttl_seconds=90,
        shadow_mode=True,
        confidence_policy=confidence_policy,
        execution_policy=execution_policy,
        anomaly_policy=anomaly_policy,
        cooldown_policy=cooldown_policy,
        governance_policy=governance_policy,
    )
    payload = aggregator.build_decision_cache(pair_snapshots)
    append_decision_history(payload)
    write_approval_summary_report({
        "pairs": {
            pair: {
                "governance_gate": meta.get("governance_gate"),
                "trading_mode": meta.get("trading_mode"),
                "governance_gatekeeper": meta.get("governance_gatekeeper"),
                "anomaly_guard": meta.get("anomaly_guard"),
                "cooldown_guard": meta.get("cooldown_guard"),
            }
            for pair, meta in payload.get("pairs", {}).items()
        }
    })
    out = Path("user_data/agent_runtime/state/decision_cache.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
