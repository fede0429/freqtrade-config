from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class IncidentAction:
    code: str
    severity: str
    priority: int
    owner: str
    auto_repairable: bool
    recommended_script: str | None
    summary: str
    why_it_matters: str
    remediation_steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SEVERITY_RANK = {'ok': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}


def severity_rank(value: str) -> int:
    return _SEVERITY_RANK.get(value, 0)


def classify_incident(*, code: str, severity: str, message: str) -> IncidentAction:
    if code == 'filled_unreconciled_orders':
        return IncidentAction(
            code=code,
            severity=severity,
            priority=100,
            owner='execution-ops',
            auto_repairable=True,
            recommended_script='scripts/ops/auto_repair_signal_pipeline.py --fix unreconciled --profile <execution_profile>',
            summary=message,
            why_it_matters='Filled orders without trade reconciliation break realized PnL attribution and make execution quality metrics unreliable.',
            remediation_steps=[
                'Run the auto-repair script with a trades DB or execution profile to retry reconciliation for unreconciled filled orders.',
                'If strong-key mapping is missing, verify external_order_id / venue_order_id propagation from the real executor.',
                'Replay one affected order to confirm dispatch, fill sync, and reconciliation events line up.',
            ],
        )
    if code == 'execution_state_anomalies':
        return IncidentAction(
            code=code,
            severity=severity,
            priority=90,
            owner='execution-platform',
            auto_repairable=False,
            recommended_script='apps/execution/replay_execution_trace.py --order-id <order_id>',
            summary=message,
            why_it_matters='Illegal state transitions usually indicate ordering bugs, duplicate callbacks, or out-of-band status updates.',
            remediation_steps=[
                'Replay one anomalous order and inspect execution_order_events in time order.',
                'Check whether the executor sent duplicate or stale status updates.',
                'Patch the connector or lifecycle rule before enabling more retries or replacements.',
            ],
        )
    if code == 'duplicate_dispatches':
        return IncidentAction(
            code=code,
            severity=severity,
            priority=70,
            owner='execution-platform',
            auto_repairable=False,
            recommended_script='scripts/ops/assess_signal_pipeline_stability.py --signal-pipeline-db <db> --execution-db <db>',
            summary=message,
            why_it_matters='Duplicate dispatches can inflate exposure and make downstream reconciliation ambiguous.',
            remediation_steps=[
                'Confirm the dispatch request hash is stable across retries.',
                'Inspect duplicate rows in execution_dispatch_log and compare payload hashes.',
                'Tighten the idempotency key if duplicates came from equivalent payloads with cosmetic differences.',
            ],
        )
    if code == 'pipeline_trace_gap':
        return IncidentAction(
            code=code,
            severity=severity,
            priority=60,
            owner='data-platform',
            auto_repairable=True,
            recommended_script='scripts/ops/auto_repair_signal_pipeline.py --fix trace',
            summary=message,
            why_it_matters='Missing trace fields weaken replay, incident triage, and end-to-end accountability.',
            remediation_steps=[
                'Run trace backfill for signal, decision, shadow, and execution rows.',
                'Check recent writes for missing run_id / trace_id propagation.',
                'Rebuild the daily close health pack to verify coverage returned to 100%.',
            ],
        )
    return IncidentAction(
        code=code,
        severity=severity,
        priority=10,
        owner='platform',
        auto_repairable=False,
        recommended_script=None,
        summary=message,
        why_it_matters='Operational issue detected in the signal pipeline.',
        remediation_steps=['Review the incident details and replay affected entities before applying manual fixes.'],
    )


def enrich_incidents(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in incidents:
        action = classify_incident(code=str(item.get('code')), severity=str(item.get('severity', 'medium')), message=str(item.get('message', '')))
        merged = dict(item)
        merged.update(action.to_dict())
        enriched.append(merged)
    enriched.sort(key=lambda x: (-severity_rank(str(x.get('severity', 'ok'))), -int(x.get('priority', 0)), str(x.get('code', ''))))
    return enriched


def build_next_actions(incidents: list[dict[str, Any]]) -> list[str]:
    if not incidents:
        return ['No action required. Continue normal daily close review.']
    actions: list[str] = []
    for item in incidents[:5]:
        script = item.get('recommended_script')
        if script:
            actions.append(f"{item['code']}: {item['summary']} Run `{script}`.")
        else:
            actions.append(f"{item['code']}: {item['summary']} Owner={item.get('owner', 'platform')}.")
    return actions


def summarize_disposition(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    if not incidents:
        return {'status': 'clear', 'highest_severity': 'ok', 'auto_repairable_count': 0, 'owners': []}
    highest = max((str(item.get('severity', 'ok')) for item in incidents), key=severity_rank)
    auto_repairable = sum(1 for item in incidents if item.get('auto_repairable'))
    owners = sorted({str(item.get('owner', 'platform')) for item in incidents})
    status = 'page-now' if severity_rank(highest) >= severity_rank('high') else 'review-today'
    return {
        'status': status,
        'highest_severity': highest,
        'auto_repairable_count': auto_repairable,
        'owners': owners,
    }
