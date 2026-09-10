# archive/ — orphaned builders (moved 2026-09-10, branch `chore/audit-dead-weight-2026-09-10`)

These files had **zero references** across `refresh_pipeline.py`, all `.github/workflows/*.yml`,
`index.html`, `intelligence-web.html`, `js/**`, root `*.js`, `tests/*`, and `validate_*.py`
(verified by grep; see `AUDIT_DEAD_WEIGHT.md` §2 for the per-file evidence table).

- `build_event_pipeline.py` + `build_event_history/consistency/intelligence/market_impact/resolution.py` — dead orchestrator cluster (only self-refs).
- `update8_global_layers.py`, `update9_live_reporting.py` — superseded stage-numbered collectors.
- `update_osint.py`, `update_cfr.py`, `update_macro_data.py` — superseded collectors.
- `update_political_intelligence.py`, `update_political_layer.py` — uncalled.
- `update_conflict_dataset.py` — uncalled (distinct from the live `update_conflict_coverage.py`).
- `build_historical_trends.py` — uncalled.

Restoring: `git mv archive/<file>.py ./` — but first confirm no name collision with a live builder.
No import shims were added because no live module imports any of these (verified).
