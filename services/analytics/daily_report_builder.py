from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.analytics.report_loader import load_json, load_optional_signal_pipeline, load_reporting_input
from services.analytics.report_types import OperationsReport, ReportSummary, StrategyHealth


class DailyReportBuilder:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile

    def build(self) -> OperationsReport:
        scanner = load_json(self.profile['paths']['scanner_report'])
        manifest = load_json(self.profile['paths']['strategy_manifest'])
        risk = load_json(self.profile['paths']['risk_profile'])
        reporting_input = load_reporting_input(self.profile)
        pnl = reporting_input.payload
        signal_pipeline = load_optional_signal_pipeline(self.profile, pnl['date'])

        equity_start = float(pnl['equity_start'])
        realized = float(pnl['realized_pnl'])
        unrealized = float(pnl['unrealized_pnl'])
        fees = float(pnl.get('fees', 0.0))
        net_pnl = realized + unrealized - fees
        return_pct = (net_pnl / equity_start * 100.0) if equity_start else 0.0

        summary = ReportSummary(
            date=pnl['date'],
            market_type=self.profile['market_type'],
            profile_name=self.profile['profile_name'],
            equity_start=equity_start,
            equity_end=float(pnl['equity_end']),
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            net_pnl=net_pnl,
            return_pct=round(return_pct, 2),
            fees=fees,
            open_positions=len(pnl.get('open_positions', [])),
            closed_trades=len(pnl.get('closed_trades', [])),
        )

        strategies = self._build_strategy_health(manifest, pnl)
        top_winners, top_losers = self._compute_trade_buckets(pnl)

        risk_summary = {
            'profile_name': risk.get('risk_profile_name'),
            'daily_loss_limit_ratio': risk['guards']['daily_loss_limit_ratio'],
            'weekly_loss_limit_ratio': risk['guards']['weekly_loss_limit_ratio'],
            'max_drawdown_ratio': risk['guards']['max_drawdown_ratio'],
            'current_drawdown_ratio': pnl.get('max_drawdown_ratio', 0.0),
            'guard_status': 'healthy' if pnl.get('max_drawdown_ratio', 0.0) < risk['guards']['max_drawdown_ratio'] else 'trip',
            'scanner_gate_required': risk['execution'].get('require_scanner_approval', False),
        }

        scanner_summary = {
            'market_regime': scanner['market_regime'],
            'tradable_pairs': scanner['tradable_pairs'],
            'risk_flags': scanner['risk_flags'],
            'selected_count': scanner['metadata'].get('selected_count', len(scanner['tradable_pairs'])),
        }

        data_sources = {
            'pnl_input_type': reporting_input.source_meta.get('type', 'unknown'),
            'scanner_input_type': scanner.get('metadata', {}).get('source_mode', 'unknown'),
            'scanner_report_path': self.profile['paths']['scanner_report'],
            'pnl_source_path': reporting_input.source_meta.get('path'),
            'scanner_candidate_count': scanner.get('metadata', {}).get('candidate_count'),
            'db_path_basename': reporting_input.source_meta.get('db_path_basename'),
            'db_exists': reporting_input.source_meta.get('db_exists'),
            'db_is_fixture': reporting_input.source_meta.get('db_is_fixture'),
            'db_last_modified': reporting_input.source_meta.get('db_last_modified'),
            'closed_trade_count': reporting_input.source_meta.get('closed_trade_count'),
            'open_trade_count': reporting_input.source_meta.get('open_trade_count'),
            'signal_pipeline_db': signal_pipeline.get('db_path'),
            'signal_pipeline_available': signal_pipeline.get('available', False),
        }

        narrative = self._build_narrative(summary, scanner_summary, risk_summary, strategies, data_sources, signal_pipeline)
        narrative.append(f"PnL input source was {data_sources['pnl_input_type']}.")
        if data_sources.get('db_path_basename'):
            narrative.append(
                f"SQLite input {data_sources['db_path_basename']} exists={data_sources['db_exists']} fixture={data_sources['db_is_fixture']} updated={data_sources['db_last_modified']}."
            )
        narrative.append(f"Scanner input source was {data_sources['scanner_input_type']}.")

        return OperationsReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            scanner=scanner_summary,
            risk=risk_summary,
            data_sources=data_sources,
            strategies=strategies,
            top_winners=top_winners,
            top_losers=top_losers,
            risk_events=pnl.get('risk_events', []),
            execution_funnel=signal_pipeline.get('execution_funnel', {}),
            missed_alpha=signal_pipeline.get('missed_alpha', {}),
            decision_to_fill=signal_pipeline.get('decision_to_fill', {}),
            outcome_comparison=signal_pipeline.get('outcome_comparison', {}),
            replace_cost_analysis=signal_pipeline.get('replace_cost_analysis', {}),
            integrity_checks=signal_pipeline.get('integrity_checks', {}),
            traceability=signal_pipeline.get('traceability', {}),
            alert_summary=signal_pipeline.get('alert_summary', {}),
            health_pack=signal_pipeline.get('health_pack', {}),
            narrative=narrative,
        )

    def _build_strategy_health(self, manifest: dict[str, Any], pnl: dict[str, Any]) -> list[StrategyHealth]:
        exposures: dict[str, float] = defaultdict(float)
        open_positions: dict[str, int] = defaultdict(int)
        realized: dict[str, float] = defaultdict(float)
        for item in pnl.get('open_positions', []):
            exposures[item['strategy']] += float(item.get('exposure_usd', 0.0))
            open_positions[item['strategy']] += 1
        for item in pnl.get('closed_trades', []):
            realized[item['strategy']] += float(item.get('pnl_usd', 0.0))
        out: list[StrategyHealth] = []
        runtime_key = 'paper_runtime' if self.profile['profile_name'] != 'prod' else 'prod_runtime'
        for item in manifest.get('strategies', []):
            runtime = item[runtime_key]
            rpnl = round(realized.get(item['name'], 0.0), 2)
            exposure = round(exposures.get(item['name'], 0.0), 2)
            status = 'active' if exposure > 0 or rpnl != 0 else 'idle'
            out.append(StrategyHealth(
                name=item['name'],
                stage=item['lifecycle_stage'],
                market=item['market'],
                risk_budget_fraction=float(runtime.get('risk_budget_fraction', 0.0)),
                exposure_usd=exposure,
                realized_pnl=rpnl,
                open_positions=open_positions.get(item['name'], 0),
                status=status,
            ))
        return out

    def _compute_trade_buckets(self, pnl: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        trades = list(pnl.get('closed_trades', []))
        winners = sorted([t for t in trades if t.get('pnl_usd', 0.0) >= 0], key=lambda x: x['pnl_usd'], reverse=True)[:3]
        losers = sorted([t for t in trades if t.get('pnl_usd', 0.0) < 0], key=lambda x: x['pnl_usd'])[:3]
        return winners, losers

    def _build_narrative(self, summary: ReportSummary, scanner: dict[str, Any], risk: dict[str, Any], strategies: list[StrategyHealth], data_sources: dict[str, Any], signal_pipeline: dict[str, Any]) -> list[str]:
        active = [s for s in strategies if s.status == 'active']
        notes = [
            f'Net daily result was {summary.net_pnl:.2f} USD ({summary.return_pct:.2f}%) across {summary.closed_trades} closed trades.',
            f"Scanner classified the market as {scanner['market_regime']['regime']} and approved {len(scanner['tradable_pairs'])} tradable pairs.",
        ]
        if scanner.get('risk_flags'):
            notes.append('Market-level warnings: ' + ', '.join(scanner['risk_flags']) + '.')
        if active:
            lead = max(active, key=lambda item: item.realized_pnl)
            notes.append(f'Best contributing active strategy was {lead.name} at {lead.realized_pnl:.2f} USD realized PnL.')
        notes.append(f"Risk guard status remained {risk['guard_status']} with current drawdown {risk['current_drawdown_ratio']:.4f}.")
        if data_sources['scanner_input_type'] != 'live':
            notes.append(f"Scanner is not live yet; current source mode is {data_sources['scanner_input_type']}.")
        if signal_pipeline.get('available'):
            funnel = signal_pipeline.get('execution_funnel', {})
            missed = signal_pipeline.get('missed_alpha', {})
            notes.append(
                f"Execution funnel: {funnel.get('signals', 0)} signals -> {funnel.get('decision_accept_or_reduce', 0)} accepted/reduced -> {funnel.get('execution_dispatched', 0)} dispatched -> {funnel.get('execution_filled', 0)} filled."
            )
            fill = signal_pipeline.get('decision_to_fill', {})
            notes.append(
                f"Decision-to-fill quality: fill_rate={fill.get('fill_rate_vs_dispatched', 0.0):.2%}, avg_slippage={fill.get('avg_slippage_bps', 0.0):.2f} bps, fees={fill.get('total_execution_fees', 0.0):.4f}."
            )
            notes.append(
                f"Missed alpha watch: {missed.get('profitable_rejected_shadow', 0)} profitable rejected/delayed shadows out of {missed.get('total_rejected_shadow', 0)} tracked."
            )
            alerts = signal_pipeline.get('alert_summary', {})
            if alerts:
                notes.append(
                    f"Operational alerts: severity={alerts.get('severity', 'ok')}, count={alerts.get('alert_count', 0)}, disposition={alerts.get('disposition', {}).get('status', 'clear')}."
                )
            outcome = signal_pipeline.get('outcome_comparison', {})
            if outcome:
                notes.append(
                    f"Outcome comparison: accepted real trades avg_ratio={outcome.get('accepted_trade_avg_ratio', 0.0):.4f}, rejected shadow avg_ratio={outcome.get('rejected_shadow_avg_ratio', 0.0):.4f}, gap={outcome.get('actual_vs_rejected_shadow_ratio_gap', 0.0):.4f}, strong_recon={outcome.get('strong_reconciled_trades', 0)}."
                )
            replace_cost = signal_pipeline.get('replace_cost_analysis', {})
            if replace_cost:
                notes.append(
                    f"Replace cost: {replace_cost.get('replace_orders', 0)} replace orders, avg_slippage={replace_cost.get('avg_replace_slippage_bps', 0.0):.2f} bps, fees={replace_cost.get('total_replace_fees', 0.0):.4f}."
                )
            integrity = signal_pipeline.get('integrity_checks', {})
            if integrity:
                notes.append(
                    f"Integrity: duplicate_dispatches={integrity.get('duplicate_dispatches', 0)}, filled_unreconciled={integrity.get('filled_unreconciled_orders', 0)}, state_anomalies={integrity.get('state_anomaly_count', 0)}."
                )
            traceability = signal_pipeline.get('traceability', {})
            if traceability:
                notes.append(
                    f"Traceability: coverage={traceability.get('trace_coverage_ratio', 0.0):.2%}, runs={traceability.get('distinct_runs', 0)}, traces={traceability.get('distinct_traces', 0)}."
                )
        return notes


def render_markdown(report: OperationsReport) -> str:
    s = report.summary
    lines = [
        f'# Studio Daily Operations Report - {s.date}',
        '',
        '## Executive Summary',
        f'- Market: {s.market_type}',
        f'- Profile: {s.profile_name}',
        f'- Net PnL: {s.net_pnl:.2f} USD ({s.return_pct:.2f}%)',
        f'- Realized / Unrealized: {s.realized_pnl:.2f} / {s.unrealized_pnl:.2f} USD',
        f'- Fees: {s.fees:.2f} USD',
        f'- Open positions: {s.open_positions}',
        f'- Closed trades: {s.closed_trades}',
        '',
        '## Data Sources',
        f"- PnL input type: {report.data_sources['pnl_input_type']}",
        f"- Scanner input type: {report.data_sources['scanner_input_type']}",
        '',
        '## Market & Scanner',
        f"- Regime: {report.scanner['market_regime']['regime']}",
        f"- Market pressure: {report.scanner['market_regime']['market_pressure']}",
        f"- Tradable pairs: {', '.join(report.scanner['tradable_pairs']) if report.scanner['tradable_pairs'] else 'None'}",
        f"- Scanner risk flags: {', '.join(report.scanner['risk_flags']) if report.scanner['risk_flags'] else 'None'}",
        '',
        '## Risk Status',
        f"- Guard status: {report.risk['guard_status']}",
        f"- Current drawdown: {report.risk['current_drawdown_ratio']:.4f}",
        f"- Max drawdown threshold: {report.risk['max_drawdown_ratio']:.4f}",
        f"- Scanner approval required: {report.risk['scanner_gate_required']}",
        '',
        '## Strategy Health',
    ]
    for item in report.strategies:
        lines.append(f'- {item.name}: stage={item.stage}, status={item.status}, exposure={item.exposure_usd:.2f} USD, realized_pnl={item.realized_pnl:.2f} USD')
    lines.extend(['', '## Top Winners'])
    for item in report.top_winners:
        lines.append(f"- {item['pair']} / {item['strategy']}: {item['pnl_usd']:.2f} USD")
    lines.extend(['', '## Top Losers'])
    for item in report.top_losers:
        lines.append(f"- {item['pair']} / {item['strategy']}: {item['pnl_usd']:.2f} USD")
    lines.extend(['', '## Execution Funnel'])
    if report.execution_funnel:
        lines.append(f"- Signals: {report.execution_funnel.get('signals', 0)}")
        lines.append(f"- Accept/Reduce: {report.execution_funnel.get('decision_accept_or_reduce', 0)}")
        lines.append(f"- Delay/Reject: {report.execution_funnel.get('decision_delay_or_reject', 0)}")
        lines.append(f"- Dispatched: {report.execution_funnel.get('execution_dispatched', 0)}")
        lines.append(f"- Accepted: {report.execution_funnel.get('execution_accepted', 0)}")
        lines.append(f"- Partial: {report.execution_funnel.get('execution_partial', 0)}")
        lines.append(f"- Filled: {report.execution_funnel.get('execution_filled', 0)}")
        lines.append(f"- Failed: {report.execution_funnel.get('execution_failed', 0)}")
        lines.append(f"- Cancelled: {report.execution_funnel.get('execution_cancelled', 0)}")
        lines.append(f"- Deduplicated: {report.execution_funnel.get('execution_deduplicated', 0)}")
    else:
        lines.append('- No signal pipeline data.')
    lines.extend(['', '## Decision to Fill'])
    if report.decision_to_fill:
        lines.append(f"- Fill rate vs dispatched: {report.decision_to_fill.get('fill_rate_vs_dispatched', 0.0):.4f}")
        lines.append(f"- Avg slippage: {report.decision_to_fill.get('avg_slippage_bps', 0.0):.4f} bps")
        lines.append(f"- Total execution fees: {report.decision_to_fill.get('total_execution_fees', 0.0):.8f}")
        lines.append(f"- Avg fill latency: {report.decision_to_fill.get('avg_fill_seconds', 0.0):.4f} s")
    else:
        lines.append('- No execution lifecycle data.')

    lines.extend(['', '## Outcome Comparison'])
    if report.outcome_comparison:
        lines.append(f"- Accepted decisions: {report.outcome_comparison.get('accepted_decisions', 0)}")
        lines.append(f"- Accepted filled orders: {report.outcome_comparison.get('accepted_filled_orders', 0)}")
        lines.append(f"- Accepted reconciled trades: {report.outcome_comparison.get('accepted_reconciled_trades', 0)}")
        lines.append(f"- Accepted trade pnl: {report.outcome_comparison.get('accepted_trade_pnl_usd', 0.0):.4f} USD")
        lines.append(f"- Accepted trade avg ratio: {report.outcome_comparison.get('accepted_trade_avg_ratio', 0.0):.4f}")
        lines.append(f"- Rejected shadow count: {report.outcome_comparison.get('rejected_shadow_count', 0)}")
        lines.append(f"- Rejected shadow avg ratio: {report.outcome_comparison.get('rejected_shadow_avg_ratio', 0.0):.4f}")
        lines.append(f"- Actual vs rejected shadow ratio gap: {report.outcome_comparison.get('actual_vs_rejected_shadow_ratio_gap', 0.0):.4f}")
    else:
        lines.append('- No outcome comparison data.')

    lines.extend(['', '## Integrity Checks'])
    if report.integrity_checks:
        lines.append(f"- Duplicate dispatches: {report.integrity_checks.get('duplicate_dispatches', 0)}")
        lines.append(f"- Orphan orders: {report.integrity_checks.get('orphan_orders', 0)}")
        lines.append(f"- Filled unreconciled orders: {report.integrity_checks.get('filled_unreconciled_orders', 0)}")
        lines.append(f"- State anomaly count: {report.integrity_checks.get('state_anomaly_count', 0)}")
    else:
        lines.append('- No integrity data.')

    lines.extend(['', '## Traceability'])
    if report.traceability:
        lines.append(f"- Orders: {report.traceability.get('orders', 0)}")
        lines.append(f"- Traced orders: {report.traceability.get('traced_orders', 0)}")
        lines.append(f"- Trace coverage ratio: {report.traceability.get('trace_coverage_ratio', 0.0):.4f}")
        lines.append(f"- Distinct runs: {report.traceability.get('distinct_runs', 0)}")
        lines.append(f"- Distinct traces: {report.traceability.get('distinct_traces', 0)}")
    else:
        lines.append('- No traceability data.')

    lines.extend(['', '## Missed Alpha'])
    if report.missed_alpha:
        lines.append(f"- Rejected/Delayed shadows tracked: {report.missed_alpha.get('total_rejected_shadow', 0)}")
        lines.append(f"- Profitable rejected shadows: {report.missed_alpha.get('profitable_rejected_shadow', 0)}")
        lines.append(f"- Profitable ratio: {report.missed_alpha.get('profitable_rejected_ratio', 0.0):.4f}")
        lines.append(f"- Best rejected pnl ratio: {report.missed_alpha.get('best_rejected_ratio', 0.0):.4f}")
    else:
        lines.append('- No missed alpha data.')

    lines.extend(['', '## Risk Events'])
    for item in report.risk_events:
        lines.append(f"- [{item['severity']}] {item['type']}: {item['message']}")
    lines.extend(['', '## Replace Cost Analysis'])
    if report.replace_cost_analysis:
        lines.append(f"- Replace orders: {report.replace_cost_analysis.get('replace_orders', 0)}")
        lines.append(f"- Avg replace slippage: {report.replace_cost_analysis.get('avg_replace_slippage_bps', 0.0):.4f} bps")
        lines.append(f"- Total replace fees: {report.replace_cost_analysis.get('total_replace_fees', 0.0):.8f}")
        lines.append(f"- Avg replace price move: {report.replace_cost_analysis.get('avg_replace_price_move_bps', 0.0):.4f} bps")
        for item in report.replace_cost_analysis.get('replace_by_reason', []):
            lines.append(f"- {item['replace_reason']}: count={item['count']}, avg_slippage={item['avg_slippage_bps']:.4f} bps, fees={item['total_fees']:.8f}")
    else:
        lines.append('- No replace activity.')

    lines.extend(['', '## Strategy-level Missed Alpha'])
    if report.missed_alpha.get('strategy_missed_alpha_rank'):
        for item in report.missed_alpha.get('strategy_missed_alpha_rank', []):
            lines.append(f"- {item['strategy_name']}: rejected={item['rejected_count']}, profitable={item['profitable_count']}, avg_ratio={item['avg_pnl_ratio']:.4f}, best_ratio={item['best_pnl_ratio']:.4f}")
    else:
        lines.append('- No strategy-level missed alpha ranking.')

    lines.extend(['', '## Health Pack'])
    if getattr(report, 'health_pack', {}):
        lines.append(f"- Overall status: {report.health_pack.get('overall_status', 'unknown')}")
        for action in report.health_pack.get('recommended_actions', [])[:5]:
            lines.append(f"- Action: {action}")
    else:
        lines.append('- No health pack data.')

    lines.extend(['', '## Narrative'])
    for item in report.narrative:
        lines.append(f'- {item}')
    lines.append('')
    return '\n'.join(lines)


def write_outputs(report: OperationsReport, output_dir: str | Path) -> tuple[Path, Path]:
    import json
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    date = report.summary.date
    rendered_json = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    rendered_md = render_markdown(report)

    json_path = out / f'studio_daily_report_{date}.json'
    md_path = out / f'studio_daily_report_{date}.md'
    latest_json_path = out / f'studio_daily_report_{report.summary.market_type}_{report.summary.profile_name}_latest.json'
    latest_md_path = out / f'studio_daily_report_{report.summary.market_type}_{report.summary.profile_name}_latest.md'

    json_path.write_text(rendered_json, encoding='utf-8')
    md_path.write_text(rendered_md, encoding='utf-8')
    latest_json_path.write_text(rendered_json, encoding='utf-8')
    latest_md_path.write_text(rendered_md, encoding='utf-8')
    return json_path, md_path
