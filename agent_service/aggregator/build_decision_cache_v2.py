from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from agent_service.aggregator.decision_aggregator import DecisionAggregator
from agent_service.aggregator.provider_health_report import write_provider_health_report
from agent_service.aggregator.observability_report import write_observability_report
from agent_service.aggregator.decision_history_writer import append_decision_history
from agent_service.aggregator.approval_summary_report import write_approval_summary_report
from agent_service.aggregator.rollout_state_report import write_rollout_state_report
from agent_service.aggregator.final_readiness_checklist import FinalReadinessChecklist
from agent_service.aggregator.operator_handoff_pack import build_operator_handoff_pack
from agent_service.aggregator.review_summary_report import write_review_summary_report
from agent_service.aggregator.freeze_escalation_policy import FreezeEscalationPolicy
from agent_service.aggregator.escalation_report import write_escalation_report
from agent_service.providers.provider_base import ProviderSnapshot, SkillProvider
from agent_service.providers.provider_registry import build_default_provider_registry, build_pair_provider_map

DEFAULT_PAIRS = ["BTC/USDT", "ETH/USDT"]
ROLLOUT_CONFIG_PATH = "user_data/config/provider_rollout.json"
CONFIDENCE_POLICY_PATH = "user_data/config/confidence_policy.json"
EXECUTION_POLICY_PATH = "user_data/config/execution_policy.json"
ANOMALY_POLICY_PATH = "user_data/config/anomaly_policy.json"
COOLDOWN_POLICY_PATH = "user_data/config/cooldown_policy.json"
GOVERNANCE_POLICY_PATH = "user_data/config/governance_policy.json"
ROLLOUT_STATE_POLICY_PATH = "user_data/config/rollout_state_policy.json"
READINESS_POLICY_PATH = "user_data/config/readiness_policy.json"
FREEZE_ESCALATION_POLICY_PATH = "user_data/config/freeze_escalation_policy.json"


def load_json(path: str, default: dict) -> dict:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


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
    rollout_config = load_json(ROLLOUT_CONFIG_PATH, {"enabled_pairs": DEFAULT_PAIRS, "provider_defaults": {"tradingview_mcp": True, "dexpaprika": True}, "required_provider_names": ["tradingview_mcp", "dexpaprika"], "rollout_stage": "pair_provider_enablement_v1", "pair_provider_overrides": {}})
    confidence_policy = load_json(CONFIDENCE_POLICY_PATH, {"global_defaults": {}, "provider_weights": {}, "pair_overrides": {}})
    execution_policy = load_json(EXECUTION_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})
    anomaly_policy = load_json(ANOMALY_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})
    cooldown_policy = load_json(COOLDOWN_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})
    governance_policy = load_json(GOVERNANCE_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})
    rollout_state_policy = load_json(ROLLOUT_STATE_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})
    readiness_policy = load_json(READINESS_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})
    freeze_escalation_policy = load_json(FREEZE_ESCALATION_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})

    providers = build_default_provider_registry()
    write_provider_health_report(providers)
    write_json_report({"confidence_policy": confidence_policy}, "agent_service/reports/confidence_policy_report.json")
    write_json_report({"execution_policy": execution_policy}, "agent_service/reports/execution_policy_report.json")
    write_json_report({"anomaly_policy": anomaly_policy}, "agent_service/reports/anomaly_policy_report.json")
    write_json_report({"cooldown_policy": cooldown_policy}, "agent_service/reports/cooldown_policy_report.json")
    write_json_report({"governance_policy": governance_policy}, "agent_service/reports/governance_policy_report.json")
    write_json_report({"rollout_state_policy": rollout_state_policy}, "agent_service/reports/rollout_state_policy_report.json")
    write_json_report({"readiness_policy": readiness_policy}, "agent_service/reports/readiness_policy_report.json")
    write_json_report({"freeze_escalation_policy": freeze_escalation_policy}, "agent_service/reports/freeze_escalation_policy_report.json")

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
        rollout_policy=rollout_state_policy,
    )
    payload = aggregator.build_decision_cache(pair_snapshots)
    append_decision_history(payload)

    approval_summary = {"pairs": {
        pair: {
            "governance_gate": meta.get("governance_gate"),
            "trading_mode": meta.get("trading_mode"),
            "governance_gatekeeper": meta.get("governance_gatekeeper"),
            "anomaly_guard": meta.get("anomaly_guard"),
            "cooldown_guard": meta.get("cooldown_guard"),
        } for pair, meta in payload.get("pairs", {}).items()
    }}
    write_approval_summary_report(approval_summary)

    rollout_summary = {"pairs": {
        pair: {
            "rollout_state": meta.get("rollout_state"),
            "trading_mode": meta.get("trading_mode"),
            "rollout_state_machine": meta.get("rollout_state_machine"),
        } for pair, meta in payload.get("pairs", {}).items()
    }}
    write_rollout_state_report(rollout_summary)

    checklist = FinalReadinessChecklist(readiness_policy)
    review_summary = {"pairs": {}}
    for pair, meta in payload.get("pairs", {}).items():
        review_summary["pairs"][pair] = checklist.evaluate(
            pair=pair,
            governance_gatekeeper=meta.get("governance_gatekeeper", {}),
            rollout_state_machine=meta.get("rollout_state_machine", {}),
            execution_policy=meta.get("execution_policy", {}),
            anomaly_guard=meta.get("anomaly_guard", {}),
        )
    write_review_summary_report(review_summary)

    freeze_policy = FreezeEscalationPolicy(freeze_escalation_policy)
    escalation_summary = {"pairs": {}}
    for pair, meta in payload.get("pairs", {}).items():
        escalation_summary["pairs"][pair] = freeze_policy.evaluate(
            pair=pair,
            readiness=review_summary["pairs"].get(pair, {}),
            anomaly_guard=meta.get("anomaly_guard", {}),
            cooldown_guard=meta.get("cooldown_guard", {}),
            rollout_state_machine=meta.get("rollout_state_machine", {}),
        )
    write_escalation_report(escalation_summary)

    handoff_pack = build_operator_handoff_pack(payload)
    handoff_pack["review_summary"] = review_summary
    handoff_pack["escalation_summary"] = escalation_summary
    write_json_report(handoff_pack, "agent_service/reports/operator_handoff_pack.json")

    out = Path("user_data/agent_runtime/state/decision_cache.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
