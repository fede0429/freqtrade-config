# Release Checklist - spot / paper

- Release mode: release
- Approved: True
- Channel: paper

## Preflight Checks
- [pass] file:strategy_manifest: /mnt/data/step6work/mnt/data/studio-trading-system-step6/strategies/registry/deployment_manifest.json
- [pass] file:scanner_report: /mnt/data/step6work/mnt/data/studio-trading-system-step6/reports/scanner/latest_scan.json
- [pass] file:daily_report: /mnt/data/step6work/mnt/data/studio-trading-system-step6/reports/operations/daily/studio_daily_report_2026-03-08.json
- [pass] file:risk_profile: /mnt/data/step6work/mnt/data/studio-trading-system-step6/config/risk/runtime/spot.paper.json
- [pass] file:reporting_profile: /mnt/data/step6work/mnt/data/studio-trading-system-step6/config/reporting/runtime/spot.paper.json
- [pass] file:trading_config: /mnt/data/step6work/mnt/data/studio-trading-system-step6/config/runtime/spot.paper.dynamic.json
- [pass] file:docker_compose: /mnt/data/step6work/mnt/data/studio-trading-system-step6/docker/docker-compose.step6.yml
- [pass] scanner_selected_pairs: selected=3, minimum=2
- [pass] guard_status: current=healthy, required=healthy
- [pass] drawdown_budget: current=0.0110, limit=0.1200
- [pass] forbidden_stages: none
- [pass] profile_alignment: reporting=spot, release=spot, trading_hint=spot
- [pass] scanner_gate: required=True, selected=3

## Required Actions
- Re-render config, risk, scanner, reporting, and strategy manifests before startup.
- Capture preflight artifact and attach it to the operating log.
