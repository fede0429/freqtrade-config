from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from agent_service.providers.provider_base import ProviderHealth, SkillProvider


def build_provider_health_report(providers: Dict[str, SkillProvider]) -> dict:
    items = {}
    for name, provider in providers.items():
        health = provider.health()
        items[name] = {
            "provider": health.provider,
            "kind": health.kind,
            "status": health.status,
            "ts": health.ts,
            "detail": health.detail,
        }
    return {"providers": items}


def write_provider_health_report(
    providers: Dict[str, SkillProvider],
    output_path: str = "agent_service/reports/provider_health_report.json",
) -> Path:
    report = build_provider_health_report(providers)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
