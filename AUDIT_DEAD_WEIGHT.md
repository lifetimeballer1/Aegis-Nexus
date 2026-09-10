# AUDIT_DEAD_WEIGHT — 2026-09-10 (branch `chore/audit-dead-weight-2026-09-10`)

Goal: cut CI/data/bundle lag without deleting anything necessary. Policy: disable-don't-delete for workflows, `git mv` to `archive/` (no hard deletes) for code, never touch `data/*.json`.

## 1. Workflows (`.github/workflows/`, 16 files)

| Workflow | Trigger | Weight | Verdict |
|---|---|---|---|
| `update-snapshot.yml` | cron `*/10` + push(paths) | HIGH (30-min timeout, full pipeline + deploy) | **KEEP** — canonical refresh+deploy, owns production |
| `intelligence-brief.yml` | cron `*/5` (!!) + dispatch | MEDIUM (5-min timeout, 1 builder) | **THROTTLED → hourly** — heaviest schedule in repo (288 runs/day), shares `aegis-nexus-canonical-refresh` concurrency group with the canonical refresh (`cancel-in-progress: false` → queues behind it, rebase/push races). Consumer (`js/core/config.js` intelligenceBrief endpoint) tolerates hourly freshness. Changed to `17 * * * *` with comment. |
| `enforcer-map-watcher.yml` | cron `*/10` + push(paths) | MEDIUM (yt-dlp install + YouTube hits every run) | **KEEP** — output `data/enforcer_maps.json` is consumed (`js/core/config.js` → `mapCartel` endpoint). Flagged as future throttle candidate if YouTube rate-limits. |
| `site-monitor.yml` | cron `*/30` + push(paths) | LOW (read-only HTTP checks, no writes) | **KEEP** |
| `pages.yml` | dispatch-only (manual emergency deploy) | LOW | **KEEP** |
| `conflict-coverage.yml`, `regional-osint.yml`, `data-resilience.yml` | dispatch-only (manual recovery tools, headers say so) | LOW | **KEEP** |
| `intelligence-enhancements.yml`, `source-health.yml`, `map-event-links.yml`, `enrich-intelligence-sources.yml`, `validate-pipeline.yml` | `workflow_run` (after canonical refresh) + dispatch, guarded by `if: ... conclusion == 'success'` | LOW (5-min timeouts) | **KEEP** — chained follow-ups, not duplicative |
| `browser-smoke.yml`, `security-gates.yml`, `site-hardening.yml` | push(paths)/PR/dispatch | LOW | **KEEP** |
| Artifacts | Only `browser-smoke.yml` uploads (`artifacts/intelligence-web`); Pages artifact in canonical/pages flows | — | No large/orphaned artifacts found |

No orphaned (untriggered) jobs: every job has a live trigger. No duplicative jobs: recovery workflows are explicitly dispatch-only so they can't race canonical.

## 2. Python builders vs `refresh_pipeline.py`

Pipeline actually invokes (verified by full read): `build_sources_registry`, `news_feed_db --once`, `build_source_health`, `validate_source_health`, `build_canonical_intelligence_v3`, `repair_strategic_targets`, `repair_actor_target_roles`, `diagnose_strategic_events`, `enrich_semantic_relationships`, `trace_strategic_provenance`, `update_intelligence_web`, `build_intelligence_graph`, `build_intelligence_brain`, `ensure_major_power_nodes`, `ensure_brain_groups`, `enrich_brain_actions`, `validate_action_intelligence`, `validate_intelligence_brain`, `build_strategic_signals`, `build_what_changed`, `build_map_points`, `build_failover_state`, `validate_data_resilience`, `build_validation_results` — **all kept**.

**Archived (15 files → `archive/`, zero refs across `*.py`, `.github/workflows/*`, `index.html`, `intelligence-web.html`, `js/**`, `tests/*`, `validate_*`)**:

| File | Size | Evidence |
|---|---|---|
| `build_event_pipeline.py` (+ `build_event_history/consistency/intelligence/market_impact/resolution.py`, 6 files) | 1–10 KB | Only refs are the 5 children inside the orchestrator itself (`build_event_pipeline.py:8-12`); orchestrator has 0 external callers |
| `update8_global_layers.py` | 11 KB | 0 refs |
| `update9_live_reporting.py` | 7 KB | 0 refs |
| `update_osint.py`, `update_cfr.py`, `update_macro_data.py` | 2–10 KB | 0 refs (superseded stage-numbered collectors) |
| `update_political_intelligence.py`, `update_political_layer.py` | 4–8 KB | 0 refs |
| `update_conflict_dataset.py` | 3 KB | 0 refs (distinct from `update_conflict_coverage.py`, which is kept via `conflict-coverage.yml`) |
| `build_historical_trends.py` | 2 KB | 0 refs (homepage `historicalTrends` endpoint reads `data/event_history.json`, which no live builder writes — documented data-side gap, not widened by this move) |

**Kept but flagged (tangled refs, left in place)**: `update_snapshot.py` (27 KB, legacy full builder), `update_snapshot_fast.py`, `merge_live_news.py` (imports both + `counter_cartel_runtime.install`), `build_live_events.py`, `update_regional_osint.py`, `breaking_news.py`, `counter_cartel_runtime.py`, `enhance_counter_cartel_intelligence.py` — referenced only by each other/comments, but form a legacy chain; needs a dedicated pass, not a drive-by move. `regional_osint_v2.py` kept (used by `regional-osint.yml` recovery). `update_market_data.py` kept (in canonical compile gate). `update_brain_feedback.py` / `update_feed_expansion.py` kept (in canonical compile gate).

## 3. JS audit

- `index.html`: 9 `<script>` tags (leaflet ×2 CDN, `js/app.js` module, 6 `global_pulse_*` deferred). **No three.js/3D on homepage** — the only `3d-force-graph` include is `intelligence-web.html:202` (correct page for it).
- `intelligence-web.html`: 8 scripts incl. guard + performance + filters + controls-fix + action-flow. Canonical gate asserts `intelligence_semantic_layer.js` NOT included — honored.
- ~22 root `*.js` not referenced by either HTML or any `js/**` module (e.g. `global_pulse_assessment/breaking/coverage_ui/enhancements/events/graph/intelligence/layers/list_density/market_display/mission_control_fix/page_layout/reporting/source_health/tension*/ux_hardening`, `intelligence_action_panel/brain_web/semantic_layer/boot_repair`, `claim_intelligence.js`). Total ≈ 216 KB. They ship to `_site` via the `*.js` rsync include but are never loaded → deploy bloat, **not** render-blocking. **Left in place** (canonical workflow `node --check`s several of them; removal needs a deploy-shape review). Recommend follow-up: exclude unreferenced `*.js` from Pages rsync.
- Homepage data: `js/core/fetch.js` `loadCoreData()` fetches **19 endpoints in parallel** with 30-min localStorage cache + timeouts + one retry — sound pattern. Dominant weight is `data/snapshot.json` (9.3 MB); top-10 JSON ≈ 22 MB dir total. No sync oversized fetch beyond this (all async, cached). Real perf lever = shrink `snapshot.json`, out of scope for a dead-weight pass.

## 4. Python dead code / heavy deps

- No `pandas/numpy/scipy/sklearn/torch` imports anywhere (`grep ^import/^from` → 0 hits). No pyflakes available in env; used `py_compile` + cross-ref grep instead.
- Duplicate-builder cluster (`build_event_*`) archived (see §2).

## 5. Change implemented on this branch (low-risk only)

1. `intelligence-brief.yml`: cron `*/5 * * * *` → `17 * * * *` + comment (288 → 24 runs/day, avoids :00 contention with canonical `*/10`).
2. 15 orphaned builders `git mv` → `archive/` + `archive/README.md` manifest (no shims needed: zero importers verified).
3. Nothing else touched. `data/*.json` untouched. `refresh_pipeline.py`, `pages.yml`, all `validate_*.py` untouched.

## 6. Measurements

BEFORE (main): `validate_repository.py` → PASSED (20 browser refs, 35 JSON artifacts). `validate_performance.py` → PASS (inlineScriptBytes=0, lazyIntelligenceWeb=True). `index.html` 17,566 B / `intelligence-web.html` 19,518 B / root JS 216,032 B. data/ ≈ 22,007,148 B; top: snapshot.json 9,328 KB, canonical 2,738 KB, map_points 1,977 KB, live_articles 1,949 KB, brain 1,779 KB.
AFTER (this branch): `validate_repository.py` → PASSED (20 refs, 35 artifacts, no dupes). `validate_performance.py` → PASS (same gate values). `validate_data_resilience.py` → PASS (49 nodes / 270 edges, stories=705, liveArticles=2000, marketIndicators=26). `index.html` / `intelligence-web.html` / root JS byte-identical (no HTML/JS touched — bundle delta zero by design; the win is CI load: intelligence-brief 288 → 24 runs/day, plus 15 dead builders out of the root namespace). data/ untouched (≈22 MB, snapshot.json 9.3 MB remains the known perf lever — future work: shrink/split snapshot).
