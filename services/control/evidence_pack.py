from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class EvidencePackResult:
    day: int
    archive_dir: Path
    manifest_path: Path
    summary_path: Path
    copied_files: List[str]


def load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def discover_completed_days(evidence_root: str | Path) -> List[int]:
    root = Path(evidence_root)
    if not root.exists():
        return []
    days: List[int] = []
    for path in root.iterdir():
        if path.is_dir() and path.name.startswith('day-'):
            suffix = path.name.split('-', 1)[1]
            if suffix.isdigit():
                days.append(int(suffix))
    return sorted(days)


def next_day_number(evidence_root: str | Path) -> int:
    days = discover_completed_days(evidence_root)
    return (days[-1] + 1) if days else 1


def _copy_file(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst)


def _render_summary(manifest: Dict[str, Any]) -> str:
    lines = [
        f"# Paper Run Evidence Pack - Day {manifest['day']}",
        '',
        f"- Archived at: {manifest['archived_at']}",
        f"- As of date: {manifest['as_of_date']}",
        f"- Environment: {manifest['environment']}",
        f"- Market type: {manifest['market_type']}",
        '',
        '## Snapshot',
        f"- Program status: {manifest['snapshot']['overall_status']}",
        f"- Startup mode: {manifest['snapshot']['startup_mode']}",
        f"- Release approved: {manifest['snapshot']['release_approved']}",
        f"- Scanner source mode: {manifest['snapshot']['scanner_source_mode']}",
        f"- PnL source mode: {manifest['snapshot']['pnl_input_type']}",
        f"- Guard status: {manifest['snapshot']['guard_status']}",
        f"- Tradable pairs: {', '.join(manifest['snapshot']['tradable_pairs'])}",
        '',
        '## Archived Files',
    ]
    for item in manifest['artifacts']:
        lines.append(f"- {item['role']}: {item['archived_path']}")
    lines.extend(['', '## Operator Notes'])
    for note in manifest['operator_notes']:
        lines.append(f'- [ ] {note}')
    lines.append('')
    return '\n'.join(lines)


def archive_paper_run_day(
    *,
    evidence_root: str | Path,
    program_status_path: str | Path,
    scanner_path: str | Path,
    report_path: str | Path,
    preflight_path: str | Path,
    startup_bundle_path: str | Path,
    day: int | None = None,
) -> EvidencePackResult:
    evidence_root = Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)

    program_status = load_json(program_status_path)
    report = load_json(report_path)
    scanner = load_json(scanner_path)
    preflight = load_json(preflight_path)
    startup_bundle = load_json(startup_bundle_path)

    day_number = day if day is not None else next_day_number(evidence_root)
    archive_dir = evidence_root / f'day-{day_number:02d}'
    archive_dir.mkdir(parents=True, exist_ok=True)

    copied_files: List[str] = []
    artifacts: List[Dict[str, str]] = []
    sources = [
        ('program_status', Path(program_status_path)),
        ('scanner_report', Path(scanner_path)),
        ('daily_report', Path(report_path)),
        ('preflight_report', Path(preflight_path)),
        ('startup_bundle', Path(startup_bundle_path)),
    ]
    for role, src in sources:
        archived_name = src.name
        dst = archive_dir / archived_name
        copied_files.append(_copy_file(src, dst))
        artifacts.append({
            'role': role,
            'source_path': str(src),
            'archived_path': str(dst),
        })

    manifest = {
        'day': day_number,
        'archived_at': datetime.now(timezone.utc).isoformat(),
        'as_of_date': report.get('summary', {}).get('date', program_status.get('as_of')),
        'environment': preflight.get('environment'),
        'market_type': preflight.get('market_type'),
        'artifacts': artifacts,
        'snapshot': {
            'overall_status': program_status.get('overall_status'),
            'startup_mode': startup_bundle.get('startup_mode'),
            'release_approved': bool(preflight.get('approved')),
            'scanner_source_mode': scanner.get('metadata', {}).get('source_mode'),
            'pnl_input_type': report.get('data_sources', {}).get('pnl_input_type'),
            'guard_status': report.get('risk', {}).get('guard_status'),
            'tradable_pairs': report.get('scanner', {}).get('tradable_pairs', []),
            'closed_trades': report.get('summary', {}).get('closed_trades'),
            'net_pnl': report.get('summary', {}).get('net_pnl'),
        },
        'operator_notes': [
            'confirm no manual startup bypass occurred',
            'record any anomalies observed during this paper day',
            'attach remediation notes for any risk flags that persisted across days',
        ],
    }

    manifest_path = archive_dir / 'evidence_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    summary_path = archive_dir / 'README.md'
    summary_path.write_text(_render_summary(manifest), encoding='utf-8')

    return EvidencePackResult(
        day=day_number,
        archive_dir=archive_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        copied_files=copied_files,
    )
