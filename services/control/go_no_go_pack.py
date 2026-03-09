from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _copy(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst)


@dataclass
class GoNoGoPackResult:
    pack_dir: Path
    manifest_path: Path
    summary_path: Path
    copied_files: List[str]


def _render_summary(manifest: Dict[str, Any]) -> str:
    lines = [
        f"# Final Canary Go / No-Go Pack - {manifest['as_of']}",
        '',
        f"- Built at: {manifest['built_at']}",
        f"- Program overall status: {manifest['program_overall_status']}",
        f"- Final decision: {manifest['final_decision']}",
        f"- Decision reason: {manifest['decision_reason']}",
        '',
        '## Key Signals',
    ]
    for k, v in manifest['key_signals'].items():
        lines.append(f'- {k}: {v}')
    lines.extend(['', '## Required Actions'])
    for action in manifest['required_actions']:
        lines.append(f'- [ ] {action}')
    lines.extend(['', '## Included Files'])
    for artifact in manifest['artifacts']:
        lines.append(f"- {artifact['role']}: {artifact['archived_path']}")
    lines.append('')
    return '\n'.join(lines)


def build_go_no_go_pack(*, as_of: str, output_root: str | Path, program_status_path: str | Path, readiness_manifest_path: str | Path, budget_guard_path: str | Path, rollback_manifest_path: str | Path, continuity_path: str | Path, scorecard_path: str | Path) -> GoNoGoPackResult:
    program = _load_json(program_status_path)
    readiness = _load_json(readiness_manifest_path)
    budget = _load_json(budget_guard_path)
    rollback = _load_json(rollback_manifest_path)
    continuity = _load_json(continuity_path)
    scorecard = _load_json(scorecard_path)

    final_decision = 'go' if program.get('overall_status') == 'ready' and budget.get('status') == 'ready' else 'no_go'
    if final_decision == 'go':
        reason = 'all readiness, budget, and rollback signals are green'
    else:
        reason = budget.get('verdict') or scorecard.get('verdict') or 'one or more gating signals remain blocked'

    output_root = Path(output_root)
    pack_dir = output_root / f'go_no_go_pack_{as_of}'
    pack_dir.mkdir(parents=True, exist_ok=True)

    copied_files: List[str] = []
    artifacts: List[Dict[str, str]] = []
    for role, src in [
        ('program_status', Path(program_status_path)),
        ('readiness_manifest', Path(readiness_manifest_path)),
        ('budget_guard', Path(budget_guard_path)),
        ('rollback_manifest', Path(rollback_manifest_path)),
        ('continuity', Path(continuity_path)),
        ('scorecard', Path(scorecard_path)),
    ]:
        dst = pack_dir / src.name
        copied_files.append(_copy(src, dst))
        artifacts.append({'role': role, 'source_path': str(src), 'archived_path': str(dst)})

    manifest = {
        'as_of': as_of,
        'built_at': datetime.now(timezone.utc).isoformat(),
        'program_overall_status': program.get('overall_status'),
        'final_decision': final_decision,
        'decision_reason': reason,
        'key_signals': {
            'canary_readiness_status': scorecard.get('status'),
            'canary_budget_status': budget.get('status'),
            'rollback_status': rollback.get('rollback_status'),
            'days_completed': continuity.get('days_completed'),
            'missing_days': continuity.get('missing_days'),
            'scorecard_score': f"{scorecard.get('score')}/{scorecard.get('max_score')}",
            'budget_checks': f"{budget.get('summary', {}).get('checks_passed')}/{budget.get('summary', {}).get('checks_total')}",
        },
        'required_actions': list(dict.fromkeys(scorecard.get('required_actions', []) + budget.get('required_actions', []) + rollback.get('required_actions', []))),
        'artifacts': artifacts,
    }
    manifest_path = pack_dir / 'go_no_go_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    summary_path = pack_dir / 'README.md'
    summary_path.write_text(_render_summary(manifest), encoding='utf-8')
    return GoNoGoPackResult(pack_dir, manifest_path, summary_path, copied_files)
