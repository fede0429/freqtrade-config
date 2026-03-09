from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.control.evidence_pack import discover_completed_days


def _load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _copy(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst)


@dataclass
class CanaryReadinessPackResult:
    pack_dir: Path
    manifest_path: Path
    summary_path: Path
    copied_files: List[str]


def _render_summary(manifest: Dict[str, Any]) -> str:
    lines = [
        f"# Canary Readiness Pack - {manifest['as_of']}",
        '',
        f"- Built at: {manifest['built_at']}",
        f"- Overall program status: {manifest['program_overall_status']}",
        f"- Canary status: {manifest['scorecard']['status']}",
        f"- Canary verdict: {manifest['scorecard']['verdict']}",
        f"- Canary score: {manifest['scorecard']['score']}/{manifest['scorecard']['max_score']}",
        f"- Days completed: {manifest['continuity']['days_completed']}/{manifest['continuity']['expected_days']}",
        '',
        '## Blocking Gaps',
    ]
    gaps = manifest.get('blocking_gaps', [])
    if gaps:
        for gap in gaps:
            lines.append(f'- {gap}')
    else:
        lines.append('- None')
    lines.extend(['', '## Included Files'])
    for artifact in manifest['artifacts']:
        lines.append(f"- {artifact['role']}: {artifact['archived_path']}")
    lines.extend(['', '## Required Actions'])
    for action in manifest['required_actions']:
        lines.append(f'- [ ] {action}')
    lines.append('')
    return '\n'.join(lines)


def build_canary_readiness_pack(
    *,
    output_root: str | Path,
    as_of: str,
    program_status_path: str | Path,
    continuity_path: str | Path,
    scorecard_path: str | Path,
    evidence_root: str | Path,
    paper_run_checklist_path: Optional[str | Path] = None,
    startup_bundle_path: Optional[str | Path] = None,
    preflight_path: Optional[str | Path] = None,
) -> CanaryReadinessPackResult:
    output_root = Path(output_root)
    pack_dir = output_root / f'canary_readiness_pack_{as_of}'
    pack_dir.mkdir(parents=True, exist_ok=True)

    program = _load_json(program_status_path)
    continuity = _load_json(continuity_path)
    scorecard = _load_json(scorecard_path)

    copied_files: List[str] = []
    artifacts: List[Dict[str, str]] = []

    base_sources = [
        ('program_status', Path(program_status_path)),
        ('paper_run_continuity', Path(continuity_path)),
        ('canary_scorecard', Path(scorecard_path)),
    ]
    if paper_run_checklist_path:
        base_sources.append(('paper_run_checklist', Path(paper_run_checklist_path)))
    if startup_bundle_path:
        base_sources.append(('startup_bundle', Path(startup_bundle_path)))
    if preflight_path:
        base_sources.append(('preflight_report', Path(preflight_path)))

    for role, src in base_sources:
        dst = pack_dir / src.name
        copied_files.append(_copy(src, dst))
        artifacts.append({'role': role, 'source_path': str(src), 'archived_path': str(dst)})

    days = discover_completed_days(evidence_root)
    for day in days:
        src = Path(evidence_root) / f'day-{day:02d}' / 'evidence_manifest.json'
        if src.exists():
            dst = pack_dir / 'evidence_manifests' / src.parent.name / src.name
            copied_files.append(_copy(src, dst))
            artifacts.append({'role': f'evidence_manifest_day_{day:02d}', 'source_path': str(src), 'archived_path': str(dst)})

    blocking_gaps: List[str] = []
    if continuity.get('missing_days'):
        blocking_gaps.append(f"Missing paper-run days: {continuity['missing_days']}")
    if continuity.get('guard_fail_days'):
        blocking_gaps.append(f"Guard unhealthy on days: {continuity['guard_fail_days']}")
    if continuity.get('startup_not_armed_days'):
        blocking_gaps.append(f"Startup gate not armed on days: {continuity['startup_not_armed_days']}")
    if continuity.get('release_not_approved_days'):
        blocking_gaps.append(f"Release not approved on days: {continuity['release_not_approved_days']}")
    if continuity.get('scanner_not_live_days'):
        blocking_gaps.append(f"Scanner not live on days: {continuity['scanner_not_live_days']}")

    manifest = {
        'as_of': as_of,
        'built_at': datetime.now(timezone.utc).isoformat(),
        'program_overall_status': program.get('overall_status'),
        'continuity': {
            'days_completed': continuity.get('days_completed'),
            'expected_days': continuity.get('expected_days'),
            'missing_days': continuity.get('missing_days', []),
        },
        'scorecard': {
            'status': scorecard.get('status'),
            'verdict': scorecard.get('verdict'),
            'score': scorecard.get('score'),
            'max_score': scorecard.get('max_score'),
        },
        'blocking_gaps': blocking_gaps,
        'required_actions': scorecard.get('required_actions', []),
        'artifacts': artifacts,
    }

    manifest_path = pack_dir / 'canary_readiness_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    summary_path = pack_dir / 'README.md'
    summary_path.write_text(_render_summary(manifest), encoding='utf-8')

    return CanaryReadinessPackResult(
        pack_dir=pack_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        copied_files=copied_files,
    )
