from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.control.evidence_pack import discover_completed_days


@dataclass
class MilestoneStatus:
    name: str
    status: str
    evidence: List[str]
    next_actions: List[str]
    details: Dict[str, Any]


@dataclass
class ProgramState:
    as_of: str
    milestones: List[MilestoneStatus]

    @property
    def overall_status(self) -> str:
        statuses = {m.status for m in self.milestones}
        if 'blocked' in statuses:
            return 'blocked'
        if 'in_progress' in statuses:
            return 'in_progress'
        return 'ready'


def load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _reporting_status(report: Dict[str, Any], report_path: str | Path) -> MilestoneStatus:
    data_sources = report.get('data_sources', {})
    pnl_type = data_sources.get('pnl_input_type', 'unknown')
    has_summary = bool(report.get('summary'))
    status = 'ready' if has_summary and pnl_type == 'sqlite' else 'in_progress' if has_summary else 'blocked'
    actions = []
    if pnl_type != 'sqlite':
        actions.append('replace mock reporting source with sqlite-backed production input')
    if not has_summary:
        actions.append('ensure daily report contains summary and strategy health')
    return MilestoneStatus('operations_reporting', status, [str(report_path)], actions or ['continue daily report automation'], {
        'pnl_input_type': pnl_type,
        'closed_trades': report.get('summary', {}).get('closed_trades'),
        'open_positions': report.get('summary', {}).get('open_positions'),
    })


def _scanner_status(scanner: Dict[str, Any], scanner_path: str | Path) -> MilestoneStatus:
    source_mode = scanner.get('metadata', {}).get('source_mode', 'unknown')
    tradable_pairs = scanner.get('tradable_pairs', [])
    status = 'blocked' if not tradable_pairs else 'ready' if source_mode == 'live' else 'in_progress'
    actions = []
    if source_mode != 'live':
        actions.append(f'switch scanner source from {source_mode} to live exchange data')
    if not tradable_pairs:
        actions.append('refresh scanner until tradable_pairs is non-empty')
    return MilestoneStatus('market_intelligence', status, [str(scanner_path)], actions or ['monitor regime changes and scanner risk flags'], {
        'source_mode': source_mode,
        'selected_count': scanner.get('metadata', {}).get('selected_count'),
        'candidate_count': scanner.get('metadata', {}).get('candidate_count'),
        'market_regime': scanner.get('market_regime', {}).get('regime'),
    })


def _release_status(preflight: Dict[str, Any], preflight_path: str | Path, startup_bundle: Optional[Dict[str, Any]], startup_bundle_path: Optional[str | Path]) -> MilestoneStatus:
    startup_mode = startup_bundle.get('startup_mode') if startup_bundle else 'missing'
    approved = bool(preflight.get('approved'))
    status = 'ready' if approved and startup_mode == 'armed' else 'blocked' if not approved or startup_mode == 'blocked' else 'in_progress'
    evidence = [str(preflight_path)] + ([str(startup_bundle_path)] if startup_bundle_path else [])
    actions = list(preflight.get('required_actions', []))
    if not startup_bundle:
        actions.append('generate startup bundle from start_trader.py before next paper run')
    elif startup_mode != 'armed':
        actions.append(f'resolve startup gate state: {startup_mode}')
    return MilestoneStatus('release_gate', status, evidence, actions or ['review preflight before each launch'], {
        'approved': approved,
        'mode': preflight.get('mode'),
        'startup_mode': startup_mode,
    })


def _startup_chain_status(startup_bundle: Optional[Dict[str, Any]], startup_bundle_path: Optional[str | Path]) -> MilestoneStatus:
    if not startup_bundle:
        return MilestoneStatus('startup_chain', 'in_progress', [], ['run start_trader.py to generate a startup bundle'], {'startup_mode': 'missing'})
    startup_mode = startup_bundle.get('startup_mode', 'unknown')
    status = 'ready' if startup_mode == 'armed' else 'blocked' if startup_mode == 'blocked' else 'in_progress'
    return MilestoneStatus('startup_chain', status, [str(startup_bundle_path)] if startup_bundle_path else [], startup_bundle.get('required_actions', []) or ['review startup bundle and command preview'], {
        'startup_mode': startup_mode,
        'service_name': startup_bundle.get('service_name'),
        'release_channel': startup_bundle.get('release_channel'),
    })


def _paper_run_status(report: Dict[str, Any], scanner: Dict[str, Any], preflight: Dict[str, Any], continuity: Optional[Dict[str, Any]], scorecard: Optional[Dict[str, Any]], evidence_root: str | Path | None, continuity_path: str | Path | None, scorecard_path: str | Path | None) -> MilestoneStatus:
    healthy_guard = report.get('risk', {}).get('guard_status') == 'healthy'
    enough_pairs = len(scanner.get('tradable_pairs', [])) >= 2
    approved = bool(preflight.get('approved'))
    days = discover_completed_days(evidence_root) if evidence_root else []
    days_completed = len(days)
    scorecard_status = scorecard.get('status') if scorecard else None
    continuity_ok = not continuity.get('missing_days') if continuity else days_completed >= 7
    if scorecard_status == 'ready':
        status = 'ready'
    elif healthy_guard and enough_pairs and approved:
        status = 'in_progress'
    else:
        status = 'blocked'
    actions = [
        'run 7 consecutive paper days and archive scanner, report, and preflight outputs each day',
        'confirm guard_status stays healthy throughout the validation window',
        'review any strategy with unexplained exposure or repeated losses before canary promotion',
    ]
    if continuity and continuity.get('missing_days'):
        actions.append(f"fill missing evidence days: {continuity.get('missing_days')}")
    if scorecard and scorecard.get('required_actions'):
        actions.extend(scorecard.get('required_actions', []))
    if evidence_root:
        actions.append(f'continue archiving evidence packs under {evidence_root}')
    evidence = [str(Path(evidence_root) / f'day-{day:02d}' / 'evidence_manifest.json') for day in days] if evidence_root and days else []
    if continuity_path:
        evidence.append(str(continuity_path))
    if scorecard_path:
        evidence.append(str(scorecard_path))
    unique_actions = []
    seen = set()
    for action in actions:
        if action not in seen:
            unique_actions.append(action)
            seen.add(action)
    return MilestoneStatus('paper_run_validation', status, evidence, unique_actions, {
        'guard_status': report.get('risk', {}).get('guard_status'),
        'tradable_pairs': len(scanner.get('tradable_pairs', [])),
        'preflight_approved': approved,
        'days_completed': days_completed,
        'days_required': continuity.get('expected_days', 7) if continuity else 7,
        'evidence_root': str(evidence_root) if evidence_root else None,
        'continuity_missing_days': continuity.get('missing_days', []) if continuity else [],
        'scorecard_status': scorecard_status,
        'scorecard_score': f"{scorecard.get('score')}/{scorecard.get('max_score')}" if scorecard else None,
        'continuity_ok': continuity_ok,
    })


def _canary_readiness_status(continuity: Optional[Dict[str, Any]], continuity_path: Optional[str | Path], scorecard: Optional[Dict[str, Any]], scorecard_path: Optional[str | Path]) -> MilestoneStatus:
    if not scorecard:
        return MilestoneStatus('canary_readiness', 'in_progress', [str(continuity_path)] if continuity_path else [], ['render canary promotion scorecard after each paper-run evidence update'], {'verdict': 'missing_scorecard'})
    status = scorecard.get('status', 'in_progress')
    evidence = ([str(continuity_path)] if continuity_path else []) + ([str(scorecard_path)] if scorecard_path else [])
    details = {
        'verdict': scorecard.get('verdict'),
        'score': f"{scorecard.get('score')}/{scorecard.get('max_score')}",
        'days_completed': scorecard.get('summary', {}).get('days_completed'),
        'days_required': scorecard.get('summary', {}).get('days_required'),
        'missing_days': scorecard.get('summary', {}).get('missing_days', []),
        'scanner_not_live_days': scorecard.get('summary', {}).get('scanner_not_live_days', []),
        'continuity_ok': not continuity.get('missing_days') if continuity else None,
    }
    return MilestoneStatus('canary_readiness', status, evidence, scorecard.get('required_actions', []) or ['maintain canary readiness scorecard'], details)


def _canary_budget_status(budget_guard: Optional[Dict[str, Any]], budget_guard_path: Optional[str | Path]) -> MilestoneStatus:
    if not budget_guard:
        return MilestoneStatus('canary_budget_guard', 'in_progress', [], ['run canary budget guard before canary launch'], {'verdict': 'missing_budget_guard'})
    details = {
        'verdict': budget_guard.get('verdict'),
        'checks_passed': f"{budget_guard.get('summary', {}).get('checks_passed')}/{budget_guard.get('summary', {}).get('checks_total')}",
        'open_positions': budget_guard.get('summary', {}).get('open_positions'),
        'open_exposure_usd': budget_guard.get('summary', {}).get('open_exposure_usd'),
        'max_drawdown_ratio': budget_guard.get('summary', {}).get('max_drawdown_ratio'),
    }
    return MilestoneStatus('canary_budget_guard', budget_guard.get('status', 'in_progress'), [str(budget_guard_path)] if budget_guard_path else [], budget_guard.get('required_actions', []) or ['enforce canary budget guard'], details)


def _rollback_status(rollback_manifest: Optional[Dict[str, Any]], rollback_manifest_path: Optional[str | Path]) -> MilestoneStatus:
    if not rollback_manifest:
        return MilestoneStatus('rollback_readiness', 'in_progress', [], ['generate rollback pack whenever canary is blocked or downgraded'], {'rollback_status': 'missing'})
    rb_status = rollback_manifest.get('rollback_status', 'standby')
    status = 'blocked' if rb_status == 'required' else 'ready'
    details = {
        'rollback_status': rb_status,
        'rollback_reason': rollback_manifest.get('rollback_reason'),
        'failed_checks': rollback_manifest.get('trigger_summary', {}).get('failed_checks', []),
    }
    return MilestoneStatus('rollback_readiness', status, [str(rollback_manifest_path)] if rollback_manifest_path else [], rollback_manifest.get('required_actions', []) or ['retain rollback pack for audit'], details)


def build_program_state(preflight_path: str | Path, report_path: str | Path, scanner_path: str | Path, startup_bundle_path: str | Path | None = None, evidence_root: str | Path | None = None, continuity_path: str | Path | None = None, scorecard_path: str | Path | None = None, budget_guard_path: str | Path | None = None, rollback_manifest_path: str | Path | None = None) -> ProgramState:
    preflight = load_json(preflight_path)
    report = load_json(report_path)
    scanner = load_json(scanner_path)
    startup_bundle = load_json(startup_bundle_path) if startup_bundle_path else None
    continuity = load_json(continuity_path) if continuity_path else None
    scorecard = load_json(scorecard_path) if scorecard_path else None
    budget_guard = load_json(budget_guard_path) if budget_guard_path else None
    rollback_manifest = load_json(rollback_manifest_path) if rollback_manifest_path else None

    milestones = [
        _release_status(preflight, preflight_path, startup_bundle, startup_bundle_path),
        _scanner_status(scanner, scanner_path),
        _reporting_status(report, report_path),
        _startup_chain_status(startup_bundle, startup_bundle_path),
        _paper_run_status(report, scanner, preflight, continuity, scorecard, evidence_root, continuity_path, scorecard_path),
        _canary_readiness_status(continuity, continuity_path, scorecard, scorecard_path),
        _canary_budget_status(budget_guard, budget_guard_path),
        _rollback_status(rollback_manifest, rollback_manifest_path),
    ]
    return ProgramState(as_of=report.get('summary', {}).get('date', report.get('date', 'unknown')), milestones=milestones)
