from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.execution.release_loader import load_json
from services.execution.release_planner import ReleasePlanner


@dataclass
class StartupBundle:
    approved: bool
    startup_mode: str
    startup_target: str
    release_profile: str
    preflight_report: str
    trading_config: str
    risk_profile: str
    scanner_report: str
    daily_report: str
    strategy_manifest: str
    docker_compose: str
    service_name: str
    command_preview: list[str]
    generated_at: str
    release_channel: str
    market_type: str
    required_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            'approved': self.approved,
            'startup_mode': self.startup_mode,
            'startup_target': self.startup_target,
            'release_profile': self.release_profile,
            'preflight_report': self.preflight_report,
            'trading_config': self.trading_config,
            'risk_profile': self.risk_profile,
            'scanner_report': self.scanner_report,
            'daily_report': self.daily_report,
            'strategy_manifest': self.strategy_manifest,
            'docker_compose': self.docker_compose,
            'service_name': self.service_name,
            'command_preview': self.command_preview,
            'generated_at': self.generated_at,
            'release_channel': self.release_channel,
            'market_type': self.market_type,
            'required_actions': self.required_actions,
        }


class StartupGate:
    def __init__(self, profile_path: Path) -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.profile_path = profile_path.resolve()
        self.profile = load_json(self.profile_path)

    def run_preflight(self) -> tuple[dict[str, Any], Path]:
        decision = ReleasePlanner(self.profile).evaluate().to_dict()
        decision['generated_at'] = datetime.now(timezone.utc).isoformat()
        decision['profile_path'] = str(self.profile_path.relative_to(self.root)) if self.profile_path.is_relative_to(self.root) else str(self.profile_path)
        output_dir = self.root / self.profile['release']['preflight_output_dir']
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"preflight_{self.profile['market_type']}_{self.profile['profile_name']}.json"
        output_path.write_text(__import__('json').dumps(decision, indent=2, ensure_ascii=False), encoding='utf-8')
        return decision, output_path

    def build_bundle(self, preflight_path: Path, approved: bool) -> StartupBundle:
        paths = self.profile['paths']
        service_name = 'freqtrade-futures' if self.profile['market_type'] == 'futures' else 'freqtrade-spot'
        compose_file = self.root / paths['docker_compose']
        command_preview = [
            'docker', 'compose', '-f', str(compose_file), 'up', '-d', service_name
        ]
        startup_target = self.profile.get('deployment_target', service_name)
        startup_mode = 'armed' if approved else 'blocked'
        return StartupBundle(
            approved=approved,
            startup_mode=startup_mode,
            startup_target=startup_target,
            release_profile=str(self.profile_path.relative_to(self.root)) if self.profile_path.is_relative_to(self.root) else str(self.profile_path),
            preflight_report=str(preflight_path.relative_to(self.root)) if preflight_path.is_relative_to(self.root) else str(preflight_path),
            trading_config=paths['trading_config'],
            risk_profile=paths['risk_profile'],
            scanner_report=paths['scanner_report'],
            daily_report=paths['daily_report'],
            strategy_manifest=paths['strategy_manifest'],
            docker_compose=paths['docker_compose'],
            service_name=service_name,
            command_preview=command_preview,
            generated_at=datetime.now(timezone.utc).isoformat(),
            release_channel=self.profile['release_channel'],
            market_type=self.profile['market_type'],
            required_actions=[
                'Review preflight report before starting trader.',
                'Do not bypass blocked startup without explicitly fixing failed checks.',
            ],
        )

    def write_bundle(self, bundle: StartupBundle) -> Path:
        out_dir = self.root / 'release' / 'runtime'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"startup_bundle_{self.profile['market_type']}_{self.profile['profile_name']}.json"
        out_path.write_text(__import__('json').dumps(bundle.to_dict(), indent=2, ensure_ascii=False), encoding='utf-8')
        return out_path
