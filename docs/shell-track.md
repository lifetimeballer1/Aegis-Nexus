# Aegis Nexus — App Shell Track (S1–S16)

Converts the stacked-section single page into an app-like shell: one view at a
time, mobile tab bar + More sheet, desktop rail + contextual tabs, lazy
per-view rendering.

## Invariants

- All `#section-*` hashes stay valid routes; section IDs, `data-nav` anchors,
  `gp-nav-item` count (>=18), lazy-iframe strings and performance strings are
  preserved so static contracts keep passing.
- One view active at a time; navigation state syncs across command tabs, rail
  and mobile tabs with `aria-current`.
- Record hashes (QA deep links) are passed through untouched.

## Phases and result

- **S1–S4** Ledger; `js/core/router.js` (hash routes, redirects overview →
  dashboard, click interception, hashchange/popstate); view CSS
  (`body[data-view]` shows one section); `#main` padding cleared for the fixed
  tab bar.
- **S5** Mobile app shell: bottom tabs Home · Map · Brain · Alerts · More, with
  a More sheet for Web, News, Timeline, Briefings, Search, Sources, Markets,
  Conflicts, Situation, Settings.
- **S6** Desktop: rail + contextual command tabs unchanged; single workspace.
- **S7** Lazy per-view rendering in `js/app.js`: `VIEW_RENDER` map, activation
  hooks (map init on first visit, lazy Web frame load on activation), state
  subscription re-renders only the active view.
- **S8** Stories-first Home: "What matters now" panel moved to the top;
  headline feed removed from Home and lives in News.
- **S9** IA: Overview folds into Home (redirect); Breaking presents as News;
  Conflicts stays routable for search deep links.
- **S10–S13** Refresh renders only the active view; cross-links route then
  dispatch `gp:brain-select`; back/forward via history; focus and aria handling
  through nav sync.
- **S14** `tests/dashboard_smoke.py` routes views before asserting
  (dashboard → map → brain → intelweb → dashboard); new
  `tests/test_shell_router.py` static contracts.
- **S15** Boot measurement (below).
- **S16** Acceptance docs.

## Verification evidence

- `python -m pytest -q` → **143 passed** (includes 5 shell-router contracts).
- `node --check` on `router.js`, `app.js`, `dashboard.js`,
  `global_pulse_performance.js` → clean.
- `validate_repository.py` / `validate_performance.py` → passed.
- Browser smoke (router-aware): **PASS desktop + mobile**; Intelligence Web
  smoke **PASS** (controls + failure path).
- Boot measurement with the shell: dashboard renders **816 DOM nodes** and
  **1 iframe element (not loaded)**; the map view renders on first visit
  (**1,061 nodes** when open). Previously all 14 sections and 17 render targets
  ran at boot and the map initialized eagerly.

## Known limitations

- Core data (`loadCoreData`) still prefetches all feeds once at boot; per-view
  data deferral is a future data-layer optimization, not part of this shell
  track.
- `overview` remains in the DOM as a redirect target for old links; its
  tension detail now lives on Home.
- Deep links to record hashes keep the old in-view scroll behavior.

## Decisions

- 2026-09-10 — Smoke tests may navigate views (approved).
- 2026-09-10 — Mobile tabs: Home · Map · Brain · Alerts · More.
- 2026-09-10 — Stories-first Home; headlines move to News.
- 2026-09-10 — Overview folds into Home; Breaking renamed News; Conflicts stays
  routable.
