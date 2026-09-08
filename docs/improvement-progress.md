# Aegis Nexus — Improvement Progress

## Phase 1 — Baseline (2026-09-08, branch `phase-1-baseline`) — DONE
- Traced `index.html` → `js/app.js` → 14 modules in `js/modules/` + legacy `global_pulse_*.js` deferred scripts.
- Active renderers: `js/modules/map.js` (Leaflet, canonical), `intelligence-web.html` iframe (3D WebGL) + `js/modules/intelligence-web.js` (inline summary). Data: `refresh_pipeline.py` → `data/*.json` (keyless). Deploy: canonical refresh workflow publishes browser-only `_site` to Pages; `pages.yml` is manual-only.
- Checks: `pytest` 98 passed (excl. browser smoke); `node --check` app/fetch OK; `http.server` serves locally. Browser smoke tests NOT run (no Playwright/chromium here).
- Fix: `js/app.js` `loadModules()` now imports 14 modules concurrently (`Promise.all`) instead of serial `await` — same per-module error handling.
- Confirmed (code-read): no fetch timeout in `js/core/fetch.js`; 30-min cache vs 5-min refresh; heavy boot (~9.3MB snapshot + 14 parallel feeds + iframe double-load of graph/brain); legacy `global_pulse_core.js` targets removed DOM (`#map`, `.wrap`, `window.DATA`) with its own 30s interval + fetch.
- Suspected (needs Phase 2/3 verification): silent partial-fetch failures; `what_changed.json` empty 12h window; duplicate Web data load (iframe + module).
- Next: Phase 2 — loading/freshness in `js/core/fetch.js`, `state.js`, `config.js`.
