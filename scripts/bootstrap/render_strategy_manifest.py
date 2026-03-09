#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "strategies" / "registry" / "strategy_registry.json"
OUTPUT_PATH = ROOT / "strategies" / "registry" / "deployment_manifest.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    registry = load_json(REGISTRY_PATH)
    manifest = {"generated_from": str(REGISTRY_PATH.relative_to(ROOT)), "strategies": []}
    for item in registry["strategies"]:
        params_root = ROOT / item["params_path"]
        base = load_json(params_root / "base.json")
        paper = load_json(params_root / "paper.json")
        prod = load_json(params_root / "prod.json")
        manifest["strategies"].append(
            {
                "name": item["name"],
                "lifecycle_stage": item["lifecycle_stage"],
                "market": item["market"],
                "paper_runtime": {**base, **paper},
                "prod_runtime": {**base, **prod},
            }
        )
    OUTPUT_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
