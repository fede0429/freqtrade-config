# Step 9.2 - Reporter real SQLite input

## Goal
Replace mock daily metrics with a real SQLite-backed reporting input path.

## What changed
- `services/analytics/report_loader.py` now supports `input_source.type = sqlite`
- `apps/reporter/performance_report.py` still keeps the same interface, but now the profile can point to a SQLite database
- `config/reporting/env/paper.json` and `config/reporting/env/prod.json` now use a SQLite sample database
- Added `data/fixtures/reporting/freqtrade_tradesv3_sample.sqlite`
- Added `scripts/validate/validate_reporting_sqlite_input.py`

## Current status
- SQLite path works end-to-end with the sample trades database
- Daily report output is now built from `trades` rows instead of mock JSON metrics
- The next step is to point `db_path` to the real Freqtrade `tradesv3.sqlite` in the target runtime environment

## Suggested live command
```bash
PYTHONPATH=. python3 apps/reporter/performance_report.py \
  --profile config/reporting/runtime/spot.paper.json
```
