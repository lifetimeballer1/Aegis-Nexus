# Aegis Nexus — Improvement Progress

## Phase 1 — Baseline (2026-09-08, branch `phase-1-baseline`) — DONE
- Traced `index.html` → `js/app.js` → 14 modules in `js/modules/` + legacy `global_pulse_*.js` deferred scripts.
- Active renderers: `js/modules/map.js` (Leaflet, canonical), `intelligence-web.html` iframe (3D WebGL) + `js/modules/intelligence-web.js` (inline summary). Data: `refresh_pipeline.py` → `data/*.json` (keyless). Deploy: canonical refresh workflow publishes browser-only `_site` to Pages; `pages.yml` is manual-only.
- Checks: `pytest` 98 passed (excl. browser smoke); `node --check` app/fetch OK; `http.server` serves locally. Browser smoke tests NOT run (no Playwright/chromium here).
- Fix: `js/app.js` `loadModules()` now imports 14 modules concurrently (`Promise.all`) instead of serial `await` — same per-module error handling.
- Confirmed (code-read): no fetch timeout in `js/core/fetch.js`; 30-min cache vs 5-min refresh; heavy boot (~9.3MB snapshot + 14 parallel feeds + iframe double-load of graph/brain); legacy `global_pulse_core.js` targets removed DOM (`#map`, `.wrap`, `window.DATA`) with its own 30s interval + fetch.
- Suspected (needs Phase 2/3 verification): silent partial-fetch failures; `what_changed.json` empty 12h window; duplicate Web data load (iframe + module).
- Next: Phase 2 — loading/freshness in `js/core/fetch.js`, `state.js`, `config.js`.

## Phase 2 — Loading & freshness (2026-09-08, branch `phase-2-loading-freshness`) — DONE
- `js/core/config.js`: new `CONFIG.fetch` knobs (15s timeout, 25s snapshot, 1 retry, 400ms backoff).
- `js/core/fetch.js`: AbortController timeouts with truthful messages; retry for network/timeout/5xx only (no 4xx retry); result adds `stale`/`fetchedAt`; within-TTL cache fast-path no longer mislabeled stale; `loadCoreData` batches into ONE `setState` (was ~15 renders/cycle), sets `loading` only on cold boot, preserves prior data on failed feeds, keeps `lastSuccessfulFetch` unless nothing succeeded, records per-feed `state.feedMeta`.
- Verified via node harnesses (temp, uncommitted): fresh/cache/retry/timeout-bound (~110ms)/stale-fallback/404-no-retry; hard-503 preserves prior snapshot with truthful error. `pytest` 98 passed; `node --check` clean. Browser smoke NOT run (no Playwright here).
- Remaining: `js/modules/map.js#getFeed` still has no timeout (Phase 7); 30-min TTL vs 5-min refresh retained — now labeled honestly via `feedMeta` instead.
- Next: Phase 3 — code ownership (`js/modules` vs `global_pulse_*`).

## Phase 3 — Code ownership (2026-09-08, branch `phase-3-code-ownership`) — DONE
- Traced all 5 `index.html` legacy scripts; all script tags KEPT (CI `update-snapshot.yml:145`, `site-monitor.yml`, `test_regressions.py` assert their presence).
- Ownership map: `js/app.js`+`js/modules/` own all sections; `performance.js` owns lazy iframe + reduced-motion + content-visibility; `qa.js` owns onboarding + Leaflet-marker a11y + data-error alert (its claim/deep-link hooks target markup that no longer exists — dormant, kept per regression contract); `core.js` partially live (card collapse/cap, `gp.mapFilter` persist, live-news fallback); `event_pipeline.js` fully dormant (needs `.wrap`, absent); `brain_ui.js` was an infinite 100ms `.wrap` poll.
- Fixes: `performance.js#lazyIntelWeb` skips eager frames (markup owns eager; was strip/re-add churn = double graph load); `brain_ui.js` poll bounded to 50 attempts then terminates (was infinite).
- Verified: DOM-stub harness (eager src untouched, lazy deep-link cache-bust intact, brain poll exactly 50 with zero fetches); `node --check` clean; `pytest` 98 passed. Browser smoke NOT run.
- Remaining: 18 unloaded `global_pulse_*.js` files still ship to Pages via `pages.yml` rsync (Phase 10); `globalpulse:dataready` never dispatched on current page (only dormant listeners).
- Next: Phase 4 — pipeline dependability (`refresh_pipeline.py`, workflows).

## Phase 4 — Pipeline dependability (2026-09-08, branch `phase-4-pipeline-dependability`) — DONE
- Traced: `refresh_pipeline.py` builds+verifies in order, writes manifest, then read-only validators; `update-snapshot.yml` commits+deploys only after all gates — a failed refresh fails pre-commit, so the last valid release is preserved (verified by step order). `finalize_map_ui.py` touches only `index.html`; `update_brain_feedback.py` is never executed in CI.
- Fixed overlap: 9 writer workflows + manual `pages.yml` used 5 different concurrency groups from canonical (`aegis-nexus-canonical-refresh`) — single-artifact commits (incl. 3 writing `data/snapshot.json`) could land mid-refresh and be clobbered by `git add -A` + `-X theirs`. All now share the canonical group (cancel flags preserved) so writers serialize.
- Added post-rebase gate in `update-snapshot.yml`: `validate_data_resilience.py --require-manifest` re-runs after the push, before `_site` build/deploy.
- Found on main (pre-existing, NOT introduced here): `refresh_manifest.json` brain hash ≠ committed `intelligence_brain.json` (manual rebuild without re-hash). Brain itself validates (17 nodes/92 edges); content gates pass. Heals on next canonical run (rebuilds everything pre-gate); not hand-patched.
- Verified: all 16 workflow YAMLs parse; groups confirmed; `pytest` 98 passed. Actions queueing behavior NOT verifiable locally.
- Remaining: manifest covers 10 of ~20 published JSONs (brief/event_history/what_changed/live_events/regional/enforcer/links unhashed); `what_changed.json` empty-window concern carries to Phase 5.
- Next: Phase 5 — intelligence credibility.
