from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StrategyRecord:
    name: str
    market: str
    code_path: str
    params_version: str
    params_path: str
    lifecycle_stage: str
    risk_profile: str
    upgrade_gate: dict[str, Any]


class StrategyRegistry:
    def __init__(self, registry_path: str | Path) -> None:
        self.registry_path = Path(registry_path)
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self.registry_version = payload["registry_version"]
        self.records = {
            item["name"]: StrategyRecord(
                name=item["name"],
                market=item["market"],
                code_path=item["code_path"],
                params_version=item["params_version"],
                params_path=item["params_path"],
                lifecycle_stage=item["lifecycle_stage"],
                risk_profile=item["risk_profile"],
                upgrade_gate=item["upgrade_gate"],
            )
            for item in payload["strategies"]
        }

    def get(self, strategy_name: str) -> StrategyRecord:
        return self.records[strategy_name]

    def list_by_stage(self, lifecycle_stage: str) -> list[StrategyRecord]:
        return [record for record in self.records.values() if record.lifecycle_stage == lifecycle_stage]
