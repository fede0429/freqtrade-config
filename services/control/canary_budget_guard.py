from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


@dataclass
class CanaryBudgetGuardResult:
    status: str
    verdict: str
    checks: List[Dict[str, Any]]
    required_actions: List[str]
    summary: Dict[str, Any]


def evaluate_canary_budget_guard(
    *,
    canary_profile_path: str | Path,
    readiness_pack_manifest_path: str | Path,
    daily_report_path: str | Path,
    startup_bundle_path: str | Path,
    preflight_path: str | Path,
) -> CanaryBudgetGuardResult:
    canary_profile = _load_json(canary_profile_path)
    readiness = _load_json(readiness_pack_manifest_path)
    report = _load_json(daily_report_path)
    startup = _load_json(startup_bundle_path)
    preflight = _load_json(preflight_path)

    budget = canary_profile.get('budget_guard', {})
    summary = report.get('summary', {})
    risk = report.get('risk', {})
    strategy_rows = report.get('strategies', [])
    scorecard = readiness.get('scorecard', {})

    open_positions = int(summary.get('open_positions') or 0)
    open_exposure = float(sum(float(row.get('exposure_usd') or 0.0) for row in strategy_rows))
    daily_net_pnl = float(summary.get('net_pnl') or 0.0)
    equity_start = float(summary.get('equity_start') or 0.0)
    max_drawdown_ratio = float(risk.get('max_drawdown_ratio') or 0.0)
    largest_strategy_exposure = max((float(row.get('exposure_usd') or 0.0) for row in strategy_rows), default=0.0)
    largest_strategy_allocation_ratio = (largest_strategy_exposure / equity_start) if equity_start > 0 else 0.0

    checks: List[Dict[str, Any]] = []
    actions: List[str] = []

    def add_check(name: str, passed: bool, details: Dict[str, Any], action: str) -> None:
        checks.append({'name': name, 'passed': passed, 'details': details})
        if not passed:
            actions.append(action)

    add_check(
        'canary_readiness_verdict',
        scorecard.get('status') == 'ready',
        {'status': scorecard.get('status'), 'verdict': scorecard.get('verdict'), 'score': f"{scorecard.get('score')}/{scorecard.get('max_score')}"},
        'promote to canary only after canary readiness scorecard reaches ready',
    )
    add_check(
        'startup_channel_match',
        startup.get('release_channel') == budget.get('allowed_release_channel'),
        {'startup_release_channel': startup.get('release_channel'), 'allowed_release_channel': budget.get('allowed_release_channel')},
        'launch canary only through a canary release profile and startup bundle',
    )
    add_check(
        'release_gate_approved',
        bool(preflight.get('approved')),
        {'approved': preflight.get('approved'), 'mode': preflight.get('mode')},
        'fix preflight failures before entering canary budget mode',
    )
    add_check(
        'open_positions_within_limit',
        open_positions <= int(budget.get('max_open_positions') or 0),
        {'open_positions': open_positions, 'limit': budget.get('max_open_positions')},
        'reduce open positions to the canary budget limit',
    )
    add_check(
        'notional_within_limit',
        open_exposure <= float(budget.get('max_notional_usd') or 0.0),
        {'open_exposure_usd': open_exposure, 'limit_usd': budget.get('max_notional_usd')},
        'cut notional exposure to the canary budget cap',
    )
    add_check(
        'daily_loss_within_limit',
        daily_net_pnl >= -float(budget.get('max_daily_loss_usd') or 0.0),
        {'net_pnl_usd': daily_net_pnl, 'min_allowed_usd': -float(budget.get('max_daily_loss_usd') or 0.0)},
        'do not promote to canary after breaching the canary daily loss threshold',
    )
    add_check(
        'drawdown_within_limit',
        max_drawdown_ratio <= float(budget.get('max_drawdown_ratio') or 0.0),
        {'max_drawdown_ratio': max_drawdown_ratio, 'limit_ratio': budget.get('max_drawdown_ratio')},
        'resolve drawdown breach before canary launch',
    )
    add_check(
        'strategy_allocation_within_limit',
        largest_strategy_allocation_ratio <= float(budget.get('max_strategy_allocation_ratio') or 0.0),
        {'largest_strategy_allocation_ratio': largest_strategy_allocation_ratio, 'limit_ratio': budget.get('max_strategy_allocation_ratio')},
        'rebalance strategy allocation so no single strategy exceeds canary budget policy',
    )

    passed = sum(1 for c in checks if c['passed'])
    total = len(checks)
    if passed == total:
        status = 'ready'
        verdict = 'eligible_for_canary_budget'
    elif passed >= total - 2:
        status = 'in_progress'
        verdict = 'hold'
    else:
        status = 'blocked'
        verdict = 'rollback_required_before_canary'

    return CanaryBudgetGuardResult(
        status=status,
        verdict=verdict,
        checks=checks,
        required_actions=actions,
        summary={
            'checks_passed': passed,
            'checks_total': total,
            'open_positions': open_positions,
            'open_exposure_usd': open_exposure,
            'net_pnl_usd': daily_net_pnl,
            'max_drawdown_ratio': max_drawdown_ratio,
            'largest_strategy_allocation_ratio': largest_strategy_allocation_ratio,
        },
    )
