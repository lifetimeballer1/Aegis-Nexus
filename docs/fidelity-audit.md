# Phase 1 Fidelity Audit — phone views vs design refs (2026-09-14, tranche 1)

Branch: `phase1-fidelity` off `origin/main` @ `cfb1777`.
Method: static code audit (no image refs on box). Compared each phone tab's
section shell (`index.html`) + driving renderer (`js/modules/*`) against the
ref structure: Concept 01 (Command Center Dashboard), Concept 05
(Briefings/Alerts/Timeline), Concept 06 (Sources/Validation/System Health)
— all desktop 3-column analyst layouts (nav rail / center feed / right
context rail) — plus the 3 earlier mobile refs (Map-first, Market Pulse,
Universal Search order). Baseline: `pytest tests/` 190 passed before changes.

## Cross-cutting findings (apply to all tabs)

- **F1. Dual-render architecture.** `index.html` ships static Track A–E
  fixture shells (`#trackA-center`, `.td-wrap`, `#ctimelineBody`,
  `#cbriefsBody`, `#cg-wrap`) that the core renderers unconditionally
  replace via `el.innerHTML` on a healthy boot (`dashboard.js:230`,
  `alerts.js:171`, `timeline.js:127`, `briefings.js:123`,
  `search.js:142/160`). The ref-pinned Track work is therefore
  **fallback-only** — live tabs are 100% core-rendered. Keep (live >
  pinned), but every ref detail below is judged against the CORE render,
  not the Track shell. Dead-shell cleanup is a later tranche, not this one.
- **F2. No sidebars-as-drawers on mobile.** Zero `drawer`/`aside` patterns
  anywhere except the search graph's filter drawer (`cg-drawer`). Desktop
  right-rail context survives only as stacked cards or expand-in-place.
  Systematic gap for a later tranche (a shared `gp-drawer` pattern).
- **F3. Header freshness parity.** Refs carry a freshness line in every
  section header. `dashboardUpdated`, `briefingsUpdated`, `mapUpdated`,
  `searchUpdated`, `statusUpdated` exist and are wired; `alerts`,
  `timeline`, `markets` had neither the `<div>` nor the wiring.
  **FIXED this tranche** (see § Fixes).

## Per-tab gaps

### 1. Command (`#section-dashboard`, core `dashboard.js`, fallback `ccenter.js`)
Ref demands: situation header + tension pill + failing-sources flag; 6 KPI
tiles; ops strip (tension/sources/stale/markets); signal pulse row;
headlines + mini-map + priority-regions table + what-changed (3-col grid);
market pulse + source health; top signals + tension deep-dive + domain mix;
severity legend; cross-links (`View All →`) into every tab.
Exists: all of the above in the core render (situation header, KPI strip,
ops strip, pulse row, `cc-grid` 3-col, `cc-grid2`, `cc-grid3`, legend,
7 cross-links). Headline search filter + map period pills (24H/7D/30D)
present. Mini-map is a real Leaflet instance (deterministic 350-pt sample).
Gaps:
- 1a. Track-A ref-pinned tiles/segbar/sparkcards wiped on boot (see F1).
  Live KPIs are the honest superset — no action, record only.
- 1b. (minor) Tension pill color mapping reuses geo/econ/gen pill classes
  for delta sign — cosmetic, later.

### 2. Alerts (`#section-alerts`, core `alerts.js`, fallback `calerts.js`)
Ref demands: header + freshness; severity filter chips WITH live counts;
severity-grouped queue (Critical/Watch/Info); expand-in-place rows with
evidence + source attribution; acknowledge affordance; retry/error honesty.
Exists: all — count chips (`All (n)`), severity group headers with
shown/total, expand rows with evidence links + Ack + Add-to-briefing,
Acknowledgement Status panel, honest empty states. Exceeds Track-D shell.
Gaps:
- 2a. **No `alertsUpdated` header stamp (FIXED).**
- 2b. (minor) No severity legend in-tab (dashboard + timeline-tab legend
  cover it globally; acceptable).

### 3. Timeline (`#section-timeline`, core `timeline.js`, fallback `ctimeline.js`)
Ref demands: period scoping (24H/7D/30D/ALL + custom); day separators with
honest counts; severity dots + reading pane (drawer on desktop); ref pairs
the rail with tension deep-dive + domain mix + alerts feed context.
Exists: period chips + custom date range with invalid-range honesty,
day separators (`N shown` under truncation), severity dots, reading pane,
`Showing X of Y` footer. Auto widens window when empty.
Gaps:
- 3a. **No `timelineUpdated` header stamp (FIXED).**
- 3b. (larger, later tranche) Tab is rail-only: tension deep-dive, domain
  mix, alerts feed, severity legend exist ONLY in Track-B shell (wiped, F1)
  and partly on the dashboard (`cc-grid3`). Ref-fidelity means re-adding a
  compact tension + mix strip above/below the rail in this tab.

### 4. Briefings (`#section-briefings`, core `briefings.js`, fallback `cbriefs.js`)
Ref demands: daily-digest header + freshness; key judgments; top
developments with category filters + real counts; watchlist + pins;
methodology/freshness binding; analyst drafts; thumbnails; expand-in-place.
Exists: all in core render (digest header, judgments, developments with
`data-brief-filter` counts, watchlist + `My Watchlist` pins, drafts,
thumbnails via manifest + SVG fallback). `briefingsUpdated` wired.
Gaps:
- 4a. (minor) Track-E `Showing n / m` count + `No briefs match` empty copy
  were replaced by core equivalents — parity ok, no action.
- 4b. (later) No right-rail "brief detail drawer" — full brief opens
  inline; acceptable on phone, note for drawer tranche.

### 5. Map (`#section-map`, core `map.js` + `cmap.js`, Track-A `ta-map` block)
Ref demands: layer filter bar; dark operational basemap; legend with live
counts; region quick-nav chips; priority-regions table; what-changed;
tap-signal → detail drawer (not in-flow card); Gods-Eye link.
Exists: header layer buttons (All/Conflict/Hazards/Strategic/Cartel/OSINT),
Leaflet + cluster, legend, layers panel with live counts, ops list with
search, `mapSidePanel` detail card with brain links, `mapUpdated` wired,
Track-A summary block (pills, chips, table, what-changed) PRESERVED —
core map render targets `#mapContainer`/`#mapOpsBody` only, never wipes
the section. Most ref-complete tab.
Gaps:
- 5a. (later) `mapSidePanel` renders in-flow below the map, not as an
  overlay drawer — the single clearest "sidebar-as-drawer" instance for
  the drawer tranche.
- 5b. (minor) Header layer buttons lack live counts (counts live one tap
  away in the Layers panel).

### 6. Markets (`#section-markets`, core `markets.js`)
Ref demands: `Market Pulse` header + DELAYED badge + freshness; summary
strip (tracked/advancing/declining); indicator cards (price, Δ%, session
state, source link); show-more paging; not-advice footer.
Exists: everything except freshness — provider line, 3-chip summary,
cards with price/change/state/time/source, `See more` toggle, honest
empty state + disclaimer footer, DELAYED badge in header AND body.
Gaps:
- 6a. **No `marketsUpdated` header stamp (FIXED).**
- 6b. (later) No gainers/decliners filter or sort; no per-card trend
  visual. Flat grid only.

### 7. Sources (`#section-status`, core `status.js`) — Concept 06
Ref demands: KPI strip (active/reporting/issues/coverage); overall-status
hero card; registry with state filter counts + search + paging; collector
run + health panels; artifact integrity; Validation & Data Contracts;
pipeline run history; refresh pipeline health; fetch errors.
Exists: all — `statusUpdated` wired, `data-status-filter` counts,
`statusSearch`, `statusMore`, severity language throughout.
Most complete core render in the app.
Gaps:
- 7a. (minor) No per-source drill-down (drawer tranche candidate).
- 7b. (minor) Failover state summarized, not itemized per source.

## Fixes (this tranche — header freshness parity, F3)

1. `alertsUpdated` stamp: div added to `#section-alerts` header, wired in
   `renderAlerts()` (`snapshot.updatedAt` + queue count).
2. `timelineUpdated` stamp: div added to `#section-timeline` header, wired
   in `renderTimeline()` (newest visible point time).
3. `marketsUpdated` stamp: div added to `#section-markets` header, wired
   in `renderMarkets()` (feed `updatedAt`).
All vanilla, no new deps. Locked by `tests/test_gui_phase1_fidelity.py`.
`pytest tests/`: 190 → 194 passed.

## Queued for later tranches (do NOT do here)
- T2: shared `gp-drawer` pattern; first instance `mapSidePanel` overlay (5a).
- T3: timeline-tab context strip — compact tension + domain-mix (3b).
- T4: markets filter/sort (6b); dead Track-shell cleanup (F1).
