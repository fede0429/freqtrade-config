#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED_TOP = ['portfolio', 'guards', 'market', 'execution', 'dca']


def load(path: Path):
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def main(argv):
    if len(argv) != 2:
        print('Usage: validate_risk_governance.py <risk_profile.json>')
        return 2

    path = Path(argv[1])
    profile = load(path)
    errors = []
    warnings = []

    for key in REQUIRED_TOP:
        if key not in profile:
            errors.append(f'missing top-level section: {key}')

    portfolio = profile.get('portfolio', {})
    guards = profile.get('guards', {})
    market = profile.get('market', {})
    execution = profile.get('execution', {})
    dca = profile.get('dca', {})

    def ratio(name, value, allow_zero=True, upper=1.0):
        if not isinstance(value, (int, float)):
            errors.append(f'{name} must be numeric')
            return
        lower = 0.0 if allow_zero else 1e-9
        if value < lower or value > upper:
            errors.append(f'{name} must be between {lower} and {upper}')

    ratio('portfolio.reserve_cash_ratio', portfolio.get('reserve_cash_ratio', 0))
    ratio('portfolio.max_total_exposure_ratio', portfolio.get('max_total_exposure_ratio', 0), allow_zero=False)
    ratio('portfolio.max_strategy_exposure_ratio', portfolio.get('max_strategy_exposure_ratio', 0), allow_zero=False)
    ratio('portfolio.max_symbol_exposure_ratio', portfolio.get('max_symbol_exposure_ratio', 0), allow_zero=False)
    ratio('guards.daily_loss_limit_ratio', guards.get('daily_loss_limit_ratio', 0), allow_zero=False)
    ratio('guards.weekly_loss_limit_ratio', guards.get('weekly_loss_limit_ratio', 0), allow_zero=False)
    ratio('guards.max_drawdown_ratio', guards.get('max_drawdown_ratio', 0), allow_zero=False)
    ratio('market.max_market_volatility_ratio', market.get('max_market_volatility_ratio', 0), allow_zero=False)
    ratio('execution.max_slippage_ratio', execution.get('max_slippage_ratio', 0), allow_zero=True)

    if portfolio.get('max_symbol_exposure_ratio', 1) > portfolio.get('max_strategy_exposure_ratio', 0):
        warnings.append('symbol exposure exceeds strategy exposure; likely misconfigured')
    if portfolio.get('max_strategy_exposure_ratio', 1) > portfolio.get('max_total_exposure_ratio', 0):
        warnings.append('strategy exposure exceeds total exposure; likely misconfigured')
    if guards.get('daily_loss_limit_ratio', 1) > guards.get('weekly_loss_limit_ratio', 0):
        warnings.append('daily loss limit is greater than weekly loss limit')
    if not dca.get('enabled', False) and dca.get('max_additional_entries', 0) != 0:
        warnings.append('dca disabled but max_additional_entries is not 0')
    if execution.get('reject_orders_without_stop', False) and not execution.get('require_scanner_approval', False):
        warnings.append('strict stoploss policy is enabled without scanner approval gate')

    print(f'Risk profile: {path}')
    if errors:
        print('ERRORS:')
        for item in errors:
            print(f' - {item}')
    if warnings:
        print('WARNINGS:')
        for item in warnings:
            print(f' - {item}')
    if not errors and not warnings:
        print('[OK] risk governance checks passed')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
