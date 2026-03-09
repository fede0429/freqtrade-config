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
class RollbackPackResult:
    pack_dir: Path
    manifest_path: Path
    summary_path: Path
    copied_files: List[str]


def _render_summary(manifest: Dict[str, Any]) -> str:
    lines = [
        f"# Canary Rollback Pack - {manifest['as_of']}",
        '',
        f"- Built at: {manifest['built_at']}",
        f"- Rollback status: {manifest['rollback_status']}",
        f"- Reason: {manifest['rollback_reason']}",
        '',
        '## Trigger Summary',
    ]
    for k, v in manifest['trigger_summary'].items():
        lines.append(f'- {k}: {v}')
    lines.extend(['', '## Required Actions'])
    for action in manifest['required_actions']:
        lines.append(f'- [ ] {action}')
    lines.extend(['', '## Included Files'])
    for artifact in manifest['artifacts']:
        lines.append(f"- {artifact['role']}: {artifact['archived_path']}")
    lines.append('')
    return '\n'.join(lines)


def build_rollback_pack(
    *,
    output_root: str | Path,
    as_of: str,
    budget_guard_path: str | Path,
    readiness_manifest_path: str | Path,
    program_status_path: str | Path,
    startup_bundle_path: str | Path,
    preflight_path: str | Path,
    daily_report_path: str | Path,
) -> RollbackPackResult:
    output_root = Path(output_root)
    pack_dir = output_root / f'rollback_pack_{as_of}'
    pack_dir.mkdir(parents=True, exist_ok=True)

    budget_guard = _load_json(budget_guard_path)
    readiness = _load_json(readiness_manifest_path)
    program = _load_json(program_status_path)
    startup = _load_json(startup_bundle_path)
    preflight = _load_json(preflight_path)
    report = _load_json(daily_report_path)

    copied_files: List[str] = []
    artifacts: List[Dict[str, str]] = []
    for role, src in [
        ('budget_guard', Path(budget_guard_path)),
        ('readiness_manifest', Path(readiness_manifest_path)),
        ('program_status', Path(program_status_path)),
        ('startup_bundle', Path(startup_bundle_path)),
        ('preflight_report', Path(preflight_path)),
        ('daily_report', Path(daily_report_path)),
    ]:
        dst = pack_dir / src.name
        copied_files.append(_copy(src, dst))
        artifacts.append({'role': role, 'source_path': str(src), 'archived_path': str(dst)})

    failed_checks = [c['name'] for c in budget_guard.get('checks', []) if not c.get('passed')]
    rollback_status = 'required' if budget_guard.get('status') == 'blocked' else 'standby'
    rollback_reason = budget_guard.get('verdict')
    manifest = {
        'as_of': as_of,
        'built_at': datetime.now(timezone.utc).isoformat(),
        'rollback_status': rollback_status,
        'rollback_reason': rollback_reason,
        'trigger_summary': {
            'budget_guard_status': budget_guard.get('status'),
            'failed_checks': failed_checks,
            'startup_mode': startup.get('startup_mode'),
            'preflight_approved': preflight.get('approved'),
            'program_overall_status': program.get('overall_status'),
            'daily_guard_status': report.get('risk', {}).get('guard_status'),
        },
        'required_actions': budget_guard.get('required_actions', []) + [
            'freeze canary promotion until all failed checks are cleared',
            'retain this rollback pack with the corresponding canary readiness pack for audit',
        ],
        'artifacts': artifacts,
    }
    manifest_path = pack_dir / 'rollback_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    summary_path = pack_dir / 'README.md'
    summary_path.write_text(_render_summary(manifest), encoding='utf-8')
    return RollbackPackResult(pack_dir, manifest_path, summary_path, copied_files)
