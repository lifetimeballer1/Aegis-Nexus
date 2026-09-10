# GUI Polish Shift — Progress Card (2026-09-09, 16:00–17:00 America/Chicago)

Scope: GUI ONLY (`css/`, `js/modules/`, `index.html`, `intelligence-web.html`, `docs/`).
Never touched: `data/`, `artifacts/`, pipeline/build/validate/collector scripts. No push.

---

# Evening Shift — Progressive First Render (2026-09-09, ~20:20–21:30 America/Chicago)

Scope: `js/app.js` boot path + this doc. No data/pipeline/validator/test edits.
Pushed to origin/main when green.

## Change
- `0f3fde0` `feat(gui)`: progressive first render — `renderAll()` runs
  immediately after `loadModules()` (module shells/skeletons paint from
  empty state), then again after `refresh(true)` fills the 19-feed state.
  Cold visitors see structure instead of static Loading copy while the
  ~9.5MB snapshot loads. No data or pipeline changes (3 added lines).

## Verification (all green, then pushed)
- `validate_repository` / `validate_performance` / `validate_security`: PASS.
- `tests/dashboard_smoke.py` desktop + mobile: SMOKE PASS (also covers the
  new empty-state first render — fresh profiles, no page errors).
- `tests/intelligence_web_smoke.py`: RENDER + CONTROLS PASS desktop/mobile,
  FAILURE PASS.
- `pytest -q -k gui`: 61 passed. `node --test intelligence_web_filters`: 7 passed.
- Timing probe (throwaway, not committed): unthrottled localhost paints
  timeline/alerts shells at ~0.53s ahead of snapshot completion (~0.75s);
  throttled 400KB/s cold-load paints shells at ~1.4s while the 9.5MB
  snapshot needs ~25s — the gap this fix closes.

## Feed triage (read-only, no hammering — nothing actionable in GUI scope)
- `data/source_health.json` (15:35 CT): 55/63 online, 8 failed — all upstream:
  France 24 transient malformed XML (succeeded 12 min earlier, fallback
  available, self-heals); 2x GDELT rate-limited (HTTP 429 / empty reply,
  58 consecutive fails, chronic); 5x X accounts proxy-challenged (locked).
- Status panel already surfaces failed feeds honestly (counts, filters,
  chips) — no GUI gap. No pipeline edits per scope; left for automation.

## Decisions (thin spots from brief)
- **Group counts: honest labels, not full totals.** Sliced lists keep slice counts
  but label them so they never read as totals: timeline day headers read
  "N shown" under `MAX_POINTS` truncation (full totals stay in the
  "Showing X of Y signals" footer); breaking/conflicts disclose their silent
  50-item caps the same way. Search per-domain caps already honest
  ("Showing up to N per domain · M total matches" + "See all N" links).
- **Contrast bump: VERIFIED by computation.** `--muted-2` #8499ae holds ≥4.5:1
  on every surface (worst 5.26:1 on `--panel-2`); companions also ≥6:1.
  Ratios recorded in `css/tokens.css`.
- **Token drift: clean.** No `--sev-*`/`--conf-*` redeclared outside
  `css/tokens.css` (only `var()` references). Found + fixed the inverse bug:
  `var(--accent)` used in 4 JS modules but never defined → now canonical
  `--sev-info`.

## Commits (all `feat(gui)`, verified per-commit: `pytest -q -k gui` + `git diff --check`)
1. `e04e631` timeline day counts honest under truncation (`js/modules/timeline.js`)
2. `1a3ccaa` contrast audit verified with computed ratios (`css/tokens.css`)
3. `c6fe619` hover/active/disabled states for buttons, filters, tools, inputs
   (`css/components.css`, `css/dashboard.css`, `css/map.css`)
4. `c078ac2` retarget dead `.gp-main`/`.app-shell` rules to live `.gp-app-main`;
   restored mobile bottom-nav clearance; brand-mark color lockup
   (`css/layout.css`, `css/dashboard.css` comment)
5. `c38f866` map layer panel + detail use styled classes; panel title uppercase
   (`js/modules/map.js`, `css/map.css`)
6. `8fd9b5d` remove dead legacy CSS (`.gp-kpi` card family, `.gp-market-row`,
   `.gp-region-bar`, `.gp-health-issue`) + non-canonical `operational`
   severity aliases (`css/dashboard.css`)
7. `63e95d8` intelweb control hover/active/disabled, token focus ring,
   HUD collapse transition (`intelligence-web.html`)
8. `96fd539` replace undefined `--accent` token with canonical `--sev-info`
   (`js/modules/brain-timeline.js`, `intelligence-brain.js`,
   `intelligence-web.js`, `markets.js`)
9. `01475c9` breaking + conflicts disclose 50-item caps with counts
   (`js/modules/breaking.js`, `js/modules/conflicts.js`)
10. `9d93aa7` overview loading copy + brain no-match state consistency
    (`js/modules/overview.js`, `js/modules/intelligence-brain.js`)
11. `8cdcda7` markets 20-cap + collector-issue counts honest
    (`js/modules/markets.js`, `js/modules/status.js`)
12. `views.js` saved-view name input gains `aria-label` (had placeholder only).
13. `bb2a81a` map detail close selector fix (`#gpMapClose`) + brain-link hover.
14. `6edf8b4` `aria-pressed` on all filter chips (alerts/briefs/drafts/map-ops/
    status/timeline) + brain node cards.
15. `ef46aa3` map header quick-filters mirror ops filter state
    (`.gp-btn.active` style added).
16. `08d93c3` `aria-pressed` on acknowledge + watchlist pin toggles.
17. `cd6bd04` web node selection parity with brain cards
    (`selected` + `aria-pressed`, in-place sync).
18. `58b9ba3` briefings watchlist header honest over 10-item slice.
19. `9480ad8` command headline link hover affordance.
20. `a361e5b` global `.meta` micro-copy base rule (bare usages normalized).
21. `d8349b0` alert evidence links disclose 4-item cap.
22. `313a909` intelweb 3D-page toggles (filter/period/orbit/labels/flow)
    gain `aria-pressed` + period chips gain active-state sync.
23. `e58b6f6` timeline day separators are valid `<li>` items (were `<div>` in `<ol>`).
24. `a90dceb` legend blocks get `role="group"` for labeled regions.
25. `89531ad` draft save indicator (`#bdSaved`) is a live region.

## Mid-shift verification (16:20)
- `pytest -q`: 123 passed. `node --test intelligence_web_filters`: 7 passed.
- `validate_repository` / `validate_performance` / `validate_security`: PASS.
- `dashboard_smoke.py` desktop (1440) + mobile (390): SMOKE PASS both.

## Reviewed, no change (recorded so the next pass skips them)
- WebGL engine caps (500 nodes / 1500+1000 edges): perf guards far above live
  scale (~100 nodes); visible "Showing X of Y" stays truthful in practice.
- `briefings.js` inline `sources.slice(0, 4)`: illustrative list, counts carried
  by adjacent `N reports · N sources` meta.
- Legacy `gp-event-dialog` / `gp-dialog-open` hooks: dormant legacy scripts
  under the regression contract; compat CSS retained intentionally.
- `cc-pill` geo/cyber/econ/indo/dom variants + `.gp-grid-4`: intentional
  variant/utility families, kept.

## Bugs fixed along the way
- Page-width cap (`max-width:1400px`) applied to nothing (`.gp-main` dead).
- Mobile last-content overlap under fixed bottom nav (`.app-shell` dead).
- Layer-panel title/rows/detail icon rendered unstyled (bare `<strong>`/`<span>`).
- Timeline-item accent border + source links invalid (undefined token).
- Silent 50-item caps in breaking/conflicts.

## Kept intentionally (not dead CSS)
- Leaflet `leaflet-*` overrides (runtime-provided classes).
- `.sr-only` reserved a11y utility + `.gp-grid-4` utility-family completion.
- `global_pulse_tokens.css` legacy compat hooks (regression contract).
- intelweb page-scoped `--panel` glass override (deliberate, not sev/conf drift).

## Still open (re-check before 17:00)
- settings/views/app.js review; 390/1440 re-verify after shell retarget.
- Spacing rhythm: AUDITED — 2px-based scale, off-rhythm 5/7/9px values all
  justified dense/touch exceptions (no churn; recorded here).
- Full verification: validate_repository, validate_performance,
  validate_security, pytest -q, node filter tests, http.server smoke,
  `git diff --check`.
