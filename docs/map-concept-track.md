# Aegis Nexus — Global Map Concept Track (M5–M44)

Front-end-only continuation of the M1–M4 map phases, bringing the Global
Geospatial Operations Map to the same concept design language and depth as the
C/W tracks, adapted to the canonical map artifacts.

## Invariants (must not break)

- `map.js` strings: `export function renderMapOps`, `export function renderMap`,
  `mapPoints`, `markers`, `updatedAt`, `escapeHtml`, `Loading map operations`,
  `Map signals unavailable`, `data-map-ops-filter`, `mapOpsSearch`, `mapOpsBody`,
  `No signals match`, `Showing`, layer keys, `sev-`, no `lorem`, no root paths.
- M1–M4: `ensureMapSize`, `invalidateSize`, `IntersectionObserver`, `_stopped`,
  `stopPropagation`, `showDetail(p)`, `map.on('click',closeDetail)`,
  `renderMap._fitted`, `fitAll(points)`, localhost test hooks.
- M2–M4 strings: `renderFingerprint`, `renderMap._fp`, `MAP_RENDER_CAP`,
  `markerClusterGroup`, `chunkedLoading`, `disableClusteringAtZoom`,
  `spiderfyOnMaxZoom`, `preferCanvas`, `iconCreateFunction`,
  `getAllChildMarkers`, `__layer`, `marker-cluster-`, `p.brainNode?10`,
  `borderLeft`, `css/map.css` `.leaflet-tooltip` + `.marker-cluster` + `min-width:0`.
- `index.html`: `#section-map`, `#mapOpsBody`, `#mapContainer`, `#mapUpdated`,
  `data-nav="map"`, layer chip colors `#ff405f #ffd34d #4d9aff #ff8a35`,
  no `mapFilterPanel`/`data-map-filter`/`gp-map-filter-panel`.
- Smoke: `#gpMapLayers` → `#gpMapLayerPanel.open`, `#gpMapSearch`, `#gpMapReset`,
  `#gpMapCount` contains `signals` with count > 0, `gp:test-open-map-detail` →
  `#mapSidePanel` visible, `#gpMapClose` click hides it, no page errors.
- Front-end only: no pipeline/workflow/generated-JSON changes.

## Verification per phase

`pytest` (116 baseline) + `node --test tests/intelligence_web_filters.test.cjs` +
Playwright `dashboard_smoke.py` desktop/mobile + map-focused checks; report results.

## Phases

### Arc 0 — Baseline & chrome
- **M5** Ledger + baseline.
- **M6** Concept styling for toolbar, layer panel, side panel, ops rows.
- **M7** CDN resilience: honest notice when Leaflet/cluster plugin is unavailable.
- **M8** Side-panel as desktop drawer / mobile sheet, Escape + focus.

### Arc 1 — Detail & inspection
- **M9** Detail fields: confidence, importance, event type, freshness, geo note.
- **M10** Selected-marker highlight state.
- **M11** Linked event surfacing from `map_event_links` (honest candidate label).
- **M12** Brain-line caveat + accurate drawn-line count.
- **M13** Source counts/evidence in detail where present.
- **M14** Strategic-signals panel.

### Arc 2 — Layers & filters
- **M15** OSINT chip + active chip states.
- **M16** Layer-panel counts consistent with ops; panel a11y + dismiss.
- **M17** Basemap switch + labels overlay.
- **M18** Dated-signal window filter with honest undated disclosure.
- **M19** Regional intelligence panel.
- **M20** Enforcer/cartel references panel (links only, no invented coordinates).
- **M21** Severity derived from real confidence fields, not layer defaults.

### Arc 3 — Ops workspace
- **M22** Sorting + show-more.
- **M23** Severity filter chips.
- **M24** Ops↔map selection sync.
- **M25** Debounced search + memoized collect.
- **M26** Row fields (source/confidence/freshness).
- **M27** Keyboard/a11y pass on ops and toolbar.

### Arc 4 — Performance & honesty
- **M28** Remove `loadMapData` double-fetch; hydrate from core state.
- **M29** Memoized collect/classify.
- **M30** Cap disclosure + zoom-aware mini-map sampling.
- **M31** Cluster tooltip breakdown.
- **M32** Mini-map wording + shared color semantics.
- **M33** Stale/partial-feed badge.

### Arc 5 — A11y & cross-links
- **M34** `#mapContainer` role/label, live counts.
- **M35** Detail region/dialog semantics + close label.
- **M36** Map ↔ Brain/Web/event cross-links.
- **M37** Touch targets + reduced motion.
- **M38** Copy coordinates + legend semantics.

### Arc 6 — Acceptance
- **M39** Honesty cleanup (counts, caveats).
- **M40** Dead selector/dead-code cleanup.
- **M41** Fit/Reset/persistence polish.
- **M42** Shared mini-map/main-map color + sampling.
- **M43** A11y/perf audit.
- **M44** Full regression + docs.

## Decision log
- 2026-09-10 — Branch `map-concept-track` stacked on `intelweb-concept-track`.
- 2026-09-10 — Front-end only; enforcer/strategic/regional feeds surfaced as
  honest panels without invented coordinates.

## Completion status (2026-09-10)

All 40 phases landed:

- **M6–M8** concept chrome, CDN/engine notices, fixed detail drawer (desktop) /
  sheet (mobile) with Escape + close focus.
- **M9–M14** detail fields (confidence, importance, event type, freshness,
  source records, geo-precision note), selected-marker highlight, linked-event
  candidate surfacing, Brain-line caveat + accurate drawn count, strategic
  signals and cartel reference panels (links only, no invented pins).
- **M15–M21** OSINT chip + active states, layer-panel consistency with layer
  notes and dismiss/Escape, collapsed by default; regional panel; confidence-
  derived severity (no layer-hardcoded severity).
- **M22–M27** sorting, severity filters, ops↔map selection highlight, debounced
  ops search, row fields (confidence/source), ARIA pressed states.
- **M28–M33** `loadMapData` hydrates from core state (no double-fetch),
  memoized `collect()`, cap disclosure, zoom-aware mini-map sampling, cluster
  tooltips with layer counts, mini-map wording/colors, stale-feed badge.
- **M34–M38** `#mapContainer` role/label, `#gpMapCount` live region, detail
  region/close labels, Map↔Brain/Web cross-links, 44px coarse-pointer targets,
  reduced-motion guards, copy-coordinate affordance, layer-vs-severity note.
- **M39–M44** honesty wording (`mapped points`, drawn-line counts, caveats),
  dead selector fix (`#gpMapClose`), Fit/Reset preserved, shared mini-map/main
  colors, acceptance docs.

## Verification evidence (M44)

- `python -m pytest -q` → **116 passed** (all M1–M4 contracts intact).
- `node --test tests/intelligence_web_filters.test.cjs` → 7 passed.
- `validate_repository.py` / `validate_security.py` / `validate_performance.py` → passed.
- `tests/dashboard_smoke.py` → PASS desktop + mobile.
- `tests/intelligence_web_smoke.py` → RENDER/CONTROLS/FAILURE PASS.
- Custom Web inspect + bridge checks → PASS; zero page errors.
- `validate_operational_health.py` remains blocked by pre-existing snapshot
  staleness (pipeline-owned), unrelated to these GUI changes.

## Known limitations

- Region boundary overlays are not possible from available data; the priority
  region panel shows canonical counts/trends without polygons.
- Enforcer and strategic feeds publish links/signals but no incident
  coordinates; they are presented as reference panels and never pinned.
- Mini-map bubbles use a deterministic sample (zoom-aware) and cluster real
  coordinates; intra-cluster layer breakdown appears on hover only.

