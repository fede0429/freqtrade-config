#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def copy_into(src: Path, dst_dir: Path) -> str:
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return src.name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True)
    parser.add_argument('--validation-json', required=True)
    parser.add_argument('--validation-md', required=True)
    parser.add_argument('--program-status', required=True)
    parser.add_argument('--paper-checklist', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for raw in [args.profile, args.validation_json, args.validation_md, args.program_status, args.paper_checklist]:
        copied.append(copy_into(Path(raw), out_dir))

    validation = json.loads(Path(args.validation_json).read_text(encoding='utf-8'))
    manifest = {
        'status': 'ready_for_host_probe' if len(validation.get('issues', [])) <= 1 else 'blocked',
        'blocking_issues': validation.get('issues', []),
        'copied_files': copied,
        'next_action': 'Run live probe on the deployment host with network access.' if not validation.get('live_probe_ok') else 'Proceed to controlled live scanner dry run.',
    }
    (out_dir / 'live_scanner_cutover_manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )
    readme = [
        '# Live Scanner Cutover Pack',
        '',
        f"- Status: `{manifest['status']}`",
        f"- Next action: {manifest['next_action']}",
        '',
        '## Blocking issues',
        '',
    ]
    if manifest['blocking_issues']:
        readme.extend([f'- {item}' for item in manifest['blocking_issues']])
    else:
        readme.append('- none')
    readme.extend(['', '## Included files', ''])
    readme.extend([f'- `{name}`' for name in copied])
    (out_dir / 'README.md').write_text('\n'.join(readme) + '\n', encoding='utf-8')
    print(json.dumps({'output_dir': str(out_dir), 'status': manifest['status']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
