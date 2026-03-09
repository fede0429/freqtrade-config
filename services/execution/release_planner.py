from __future__ import annotations

from pathlib import Path
from typing import Any

from services.execution.deploy_types import CheckResult, ReleaseDecision
from services.execution.release_loader import load_json


class ReleasePlanner:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile
        self.root = Path(__file__).resolve().parents[2]

    def _path(self, key: str) -> Path:
        return self.root / self.profile["paths"][key]

    def evaluate(self) -> ReleaseDecision:
        checks: list[CheckResult] = []
        actions: list[str] = []
        cfg = self.profile["checks"]

        manifest = load_json(self._path("strategy_manifest"))
        scanner = load_json(self._path("scanner_report"))
        report = load_json(self._path("daily_report"))
        risk_profile = load_json(self._path("risk_profile"))
        reporting_profile = load_json(self._path("reporting_profile"))
        trading_config = load_json(self._path("trading_config"))

        required_files = {
            "strategy_manifest": self._path("strategy_manifest"),
            "scanner_report": self._path("scanner_report"),
            "daily_report": self._path("daily_report"),
            "risk_profile": self._path("risk_profile"),
            "reporting_profile": self._path("reporting_profile"),
            "trading_config": self._path("trading_config"),
            "docker_compose": self._path("docker_compose"),
        }
        for name, path in required_files.items():
            status = "pass" if path.exists() else "fail"
            checks.append(CheckResult(name=f"file:{name}", status=status, detail=str(path)))

        selected_pairs = int(scanner.get("metadata", {}).get("selected_count", len(scanner.get("tradable_pairs", []))))
        min_pairs = int(cfg.get("min_scanner_selected_pairs", 0))
        checks.append(CheckResult(
            name="scanner_selected_pairs",
            status="pass" if selected_pairs >= min_pairs else "fail",
            detail=f"selected={selected_pairs}, minimum={min_pairs}",
        ))

        guard_status = report.get("risk", {}).get("guard_status")
        required_guard_status = cfg.get("required_guard_status", "healthy")
        checks.append(CheckResult(
            name="guard_status",
            status="pass" if guard_status == required_guard_status else "fail",
            detail=f"current={guard_status}, required={required_guard_status}",
        ))

        current_drawdown = float(report.get("risk", {}).get("current_drawdown_ratio", 0.0))
        max_drawdown = float(cfg.get("max_prod_drawdown_ratio", 1.0))
        checks.append(CheckResult(
            name="drawdown_budget",
            status="pass" if current_drawdown <= max_drawdown else "fail",
            detail=f"current={current_drawdown:.4f}, limit={max_drawdown:.4f}",
        ))

        runtime_key = "prod_runtime" if self.profile["profile_name"] == "prod" else "paper_runtime"
        prod_forbidden_stages: set[str] = set()
        if cfg.get("forbid_candidate_in_prod", False) and self.profile["profile_name"] == "prod":
            prod_forbidden_stages.add("candidate")
        if cfg.get("forbid_dry_run_in_prod", False) and self.profile["profile_name"] == "prod":
            prod_forbidden_stages.add("dry_run")

        forbidden = [
            item["name"]
            for item in manifest.get("strategies", [])
            if item.get("lifecycle_stage") in prod_forbidden_stages and float(item.get(runtime_key, {}).get("risk_budget_fraction", 0.0)) > 0
        ]
        checks.append(CheckResult(
            name="forbidden_stages",
            status="pass" if not forbidden else "fail",
            detail="none" if not forbidden else ", ".join(forbidden),
        ))

        reporting_market = reporting_profile.get("market_type")
        config_market = trading_config.get("trading_mode") if self.profile["market_type"] == "futures" else "spot"
        checks.append(CheckResult(
            name="profile_alignment",
            status="pass" if reporting_market == self.profile["market_type"] else "fail",
            detail=f"reporting={reporting_market}, release={self.profile['market_type']}, trading_hint={config_market}",
        ))

        scanner_required = bool(risk_profile.get("execution", {}).get("require_scanner_approval", False))
        checks.append(CheckResult(
            name="scanner_gate",
            status="pass" if (not scanner_required or selected_pairs >= min_pairs) else "fail",
            detail=f"required={scanner_required}, selected={selected_pairs}",
        ))

        approved = all(item.status == "pass" for item in checks)
        mode = "release" if approved else "hold"

        if not approved:
            actions.append("Do not promote this environment until failed checks are resolved.")
        if self.profile["profile_name"] == "prod":
            actions.append("Confirm secrets file, docker compose override, and operator sign-off before live start.")
            actions.append("Run one last paper smoke test after final config render.")
        else:
            actions.append("Re-render config, risk, scanner, reporting, and strategy manifests before startup.")
            actions.append("Capture preflight artifact and attach it to the operating log.")

        return ReleaseDecision(
            approved=approved,
            mode=mode,
            environment=self.profile["profile_name"],
            market_type=self.profile["market_type"],
            release_channel=self.profile["release_channel"],
            checks=checks,
            required_actions=actions,
        )
