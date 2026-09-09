# GUI Polish Shift — Progress Card (2026-09-09, 16:00–17:00 America/Chicago)

Scope: GUI ONLY (`css/`, `js/modules/`, `index.html`, `intelligence-web.html`, `docs/`).
Never touched: `data/`, `artifacts/`, pipeline/build/validate/collector scripts. No push.

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
