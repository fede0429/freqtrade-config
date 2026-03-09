from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.control.evidence_pack import discover_completed_days


@dataclass
class ContinuityCheckResult:
    evidence_root: str
    days_completed: int
    expected_days: int
    missing_days: List[int]
    duplicate_days: List[int]
    guard_fail_days: List[int]
    startup_not_armed_days: List[int]
    release_not_approved_days: List[int]
    scanner_not_live_days: List[int]
    manifests: List[str]

    @property
    def is_contiguous(self) -> bool:
        return not self.missing_days

    @property
    def has_failures(self) -> bool:
        return any([
            self.missing_days,
            self.guard_fail_days,
            self.startup_not_armed_days,
            self.release_not_approved_days,
        ])


@dataclass
class CanaryPromotionScorecard:
    status: str
    score: int
    max_score: int
    verdict: str
    checks: List[Dict[str, Any]]
    required_actions: List[str]
    summary: Dict[str, Any]


def _load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_paper_run_continuity(evidence_root: str | Path, expected_days: int = 7) -> ContinuityCheckResult:
    root = Path(evidence_root)
    days = discover_completed_days(root)
    manifests: List[str] = []
    duplicate_days: List[int] = []
    guard_fail_days: List[int] = []
    startup_not_armed_days: List[int] = []
    release_not_approved_days: List[int] = []
    scanner_not_live_days: List[int] = []

    for day in days:
        day_dir = root / f'day-{day:02d}'
        manifest_path = day_dir / 'evidence_manifest.json'
        if not manifest_path.exists():
            duplicate_days.append(day)
            continue
        manifests.append(str(manifest_path))
        manifest = _load_json(manifest_path)
        snapshot = manifest.get('snapshot', {})
        if snapshot.get('guard_status') != 'healthy':
            guard_fail_days.append(day)
        if snapshot.get('startup_mode') != 'armed':
            startup_not_armed_days.append(day)
        if not bool(snapshot.get('release_approved')):
            release_not_approved_days.append(day)
        if snapshot.get('scanner_source_mode') != 'live':
            scanner_not_live_days.append(day)

    missing_days = [d for d in range(1, max(expected_days, (days[-1] if days else 0)) + 1) if d not in days]
    return ContinuityCheckResult(
        evidence_root=str(root),
        days_completed=len(days),
        expected_days=expected_days,
        missing_days=missing_days,
        duplicate_days=duplicate_days,
        guard_fail_days=guard_fail_days,
        startup_not_armed_days=startup_not_armed_days,
        release_not_approved_days=release_not_approved_days,
        scanner_not_live_days=scanner_not_live_days,
        manifests=manifests,
    )


def build_canary_promotion_scorecard(
    continuity: ContinuityCheckResult,
    *,
    min_days: int = 7,
    require_live_scanner: bool = True,
) -> CanaryPromotionScorecard:
    checks: List[Dict[str, Any]] = []
    required_actions: List[str] = []
    score = 0
    max_score = 5

    contiguous_pass = continuity.is_contiguous
    checks.append({
        'name': 'continuous_evidence_window',
        'passed': contiguous_pass,
        'details': {
            'days_completed': continuity.days_completed,
            'missing_days': continuity.missing_days,
        },
    })
    if contiguous_pass:
        score += 1
    else:
        required_actions.append('fill missing paper-run evidence days before canary promotion')

    day_count_pass = continuity.days_completed >= min_days
    checks.append({
        'name': 'minimum_days_completed',
        'passed': day_count_pass,
        'details': {
            'days_completed': continuity.days_completed,
            'days_required': min_days,
        },
    })
    if day_count_pass:
        score += 1
    else:
        required_actions.append(f'complete at least {min_days} archived paper-run days')

    guard_pass = not continuity.guard_fail_days
    checks.append({
        'name': 'risk_guard_health',
        'passed': guard_pass,
        'details': {'guard_fail_days': continuity.guard_fail_days},
    })
    if guard_pass:
        score += 1
    else:
        required_actions.append('resolve unhealthy guard days before canary promotion')

    startup_pass = not continuity.startup_not_armed_days and not continuity.release_not_approved_days
    checks.append({
        'name': 'startup_gate_discipline',
        'passed': startup_pass,
        'details': {
            'startup_not_armed_days': continuity.startup_not_armed_days,
            'release_not_approved_days': continuity.release_not_approved_days,
        },
    })
    if startup_pass:
        score += 1
    else:
        required_actions.append('ensure all archived days were started through an approved armed startup gate')

    live_pass = (not require_live_scanner) or not continuity.scanner_not_live_days
    checks.append({
        'name': 'scanner_live_source',
        'passed': live_pass,
        'details': {'scanner_not_live_days': continuity.scanner_not_live_days},
    })
    if live_pass:
        score += 1
    else:
        required_actions.append('switch scanner to live mode for the full paper-run window before canary promotion')

    if score == max_score:
        status = 'ready'
        verdict = 'eligible_for_canary'
    elif score >= 3:
        status = 'in_progress'
        verdict = 'hold'
    else:
        status = 'blocked'
        verdict = 'not_eligible'

    return CanaryPromotionScorecard(
        status=status,
        score=score,
        max_score=max_score,
        verdict=verdict,
        checks=checks,
        required_actions=required_actions,
        summary={
            'days_completed': continuity.days_completed,
            'days_required': min_days,
            'missing_days': continuity.missing_days,
            'guard_fail_days': continuity.guard_fail_days,
            'startup_not_armed_days': continuity.startup_not_armed_days,
            'release_not_approved_days': continuity.release_not_approved_days,
            'scanner_not_live_days': continuity.scanner_not_live_days,
        },
    )
