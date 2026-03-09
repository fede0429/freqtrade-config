# STEP10.2 Code Hardening

This update hardens the step10 live-scanner package in four areas:

1. Script bootstrap reliability
   - Added repo-root path bootstrap for key scripts so they no longer require `PYTHONPATH=.` to import `services.*`.
   - Added `services/common/bootstrap.py` for shared path utilities.

2. Reporting runtime safety
   - `validate_reporting_governance.py` now blocks prod profiles that still point at fixture/sample/mock sqlite databases.
   - `render_reporting_profile.py` now supports environment overrides:
     - `TRADES_DB_PATH`
     - `PAPER_TRADES_DB_PATH`
     - `PROD_TRADES_DB_PATH`
   - Prod reporting profiles now default to `/opt/trading-system/runtime/data/tradesv3_prod.sqlite` instead of sample fixture paths.

3. Reporting source observability
   - `report_loader.py` now emits sqlite source metadata:
     - basename
     - exists
     - fixture detection
     - last modified timestamp
     - closed/open trade counts
   - `daily_report_builder.py` now surfaces these in `data_sources` and narrative.

4. Live scanner cutover depth
   - `live_health.py` now checks three levels:
     - environment readiness
     - market metadata readiness
     - OHLCV probe readiness
   - It now records probe symbols, success/fail counts, latency, and error classifications.
   - Added explicit scanner runtime file names:
     - `spot.paper.scanner-fixture.json`
     - `spot.paper.scanner-live.json`
     - `futures.paper.scanner-fixture.json`
     - `spot.prod.scanner-fixture.json`
