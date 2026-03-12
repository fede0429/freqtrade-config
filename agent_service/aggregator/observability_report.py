from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from agent_service.providers.provider_base import ProviderSnapshot


def build_observability_report(pair_snapshots: Dict[str, List[ProviderSnapshot]]) -> dict:
    pairs = {}
    for pair, snapshots in pair_snapshots.items():
        pairs[pair] = {
            "provider_count": len(snapshots),
            "providers": [
                {
                    "provider": s.provider,
                    "kind": s.kind,
                    "status": s.status,
                    "latency_ms": s.latency_ms,
                    "score": s.score,
                    "stale": s.stale,
                    "risk_flags": s.risk_flags,
                }
                for s in snapshots
            ],
        }
    return {"pairs": pairs}


def write_observability_report(
    pair_snapshots: Dict[str, List[ProviderSnapshot]],
    output_path: str = "agent_service/reports/provider_observability_report.json",
) -> Path:
    report = build_observability_report(pair_snapshots)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
