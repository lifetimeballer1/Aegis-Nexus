# Aegis Nexus — Intelligence Web Concept Track (W1–W40)

Front-end-only track bringing the Intelligence Web surface to the same concept
design language and feature depth as the C1–C40 GUI track, adapted to what the
canonical `data/intelligence_graph.json` actually publishes.

## Scope and invariants

- **Front-end only.** No pipeline scripts, workflows, or generated `data/*.json`.
- **Never fabricate.** No invented nodes, edges, evidence, or metrics. Upstream
  caps (100 nodes / 500 edges) and skipped/undated evidence are disclosed honestly.
- **Preserve every test-bound contract** (see checklist below).
- **Semantic color:** blue = informational, amber = watch, red = critical,
  green = healthy. Severity is never decorative.
- **GitHub Pages:** everything must work under `/Aegis-Nexus/`.

## Invariant checklist (must not break)

- Parent `index.html`: `class="gp-intelweb-frame"`, `loading="lazy"`, literal
  `loading="eager"` absent, `#section-intelweb`, `#intelwebBody`,
  `#intelwebUpdated`, `data-nav="intelweb"`.
- Iframe script versions (asserted in `.github/workflows/update-snapshot.yml`):
  `intelligence_web_runtime_guard.js?v=20260907-guard2`,
  `intelligence_web_performance.js?v=20260907-perf2`,
  `3d-force-graph@1.79.0`, `js/intelligence_web_filters.js?v=...filters1`,
  `intelligence_web_v2.js?v=...v2`, `intelligence_web_controls_fix.js?...controlsfix2`,
  `intelligence_action_flow.js?...flow2`; `intelligence_semantic_layer.js` absent.
- Iframe ids: `#loading`, `#loading-retry`, `#graph`, `#labels`,
  `#control-toggle`, `#controls` (+ `collapsed`), `#search`, `#clear`,
  `#refresh`, `.filter[data-kind]`, `#reset`, `#orbit`, `#flow`,
  `#labels-toggle`, `#node-select`, `#stats`, `#details`, `#detail`, `#close`,
  `#trend`, `.period[data-period]`, `[data-kind="economic"]`,
  `[data-period="24"]`, `.node-label`, `window.__gpGraph`, `#graph canvas`,
  string `3D graph library failed to load`.
- Filter engine contract (`js/intelligence_web_filters.js` + node tests):
  `project()`, canonical-kind mapping, inclusive time window from source dates,
  undated/future excluded, refresh `updatedAt` is not a source time,
  case-insensitive search with direct-neighbor retention, expired edges stay
  excluded, endpoint objects tolerated, source graph never mutated.
- Graph contract: unique ids, every edge has evidence, unique
  `(source,relationship,target)`, `evidenceCount >= 1`, 100-node cap.
- Parent module strings: `export function renderIntelligenceWeb`,
  `intelligenceGraph`, `intelligenceBrain`, `getState()`, `escapeHtml`,
  `Loading relationship web`, `Intelligence Web not available`, `gpWebSearch`,
  `gpWebType`, `intelwebBody`, `data-web-node`, `No entities match`, `Showing`,
  `sev-`, `gp:brain-select`, `gpWebLoad3d`, `Loading 3D engine`; no `lorem`;
  no root-absolute paths.
- Performance gates: `global_pulse_performance.js` keeps `IntersectionObserver`,
  `requestIdleCallback`, `contentVisibility`, `prefers-reduced-motion`; inline
  scripts stay < 50 KB.

## Verification per phase

1. `python -m pytest -q` — no regressions (baseline 116).
2. `node --test tests/intelligence_web_filters.test.cjs` — 7 passing.
3. Browser: Playwright `tests/dashboard_smoke.py` and, where the CDN is
   reachable, `tests/intelligence_web_smoke.py` (desktop + mobile).
4. Report changed files, results, and browser verification explicitly.

Baseline at W1: branch `intelweb-concept-track` off `gui-concept-track`
(commit `bbeb6c2`), 116 pytest / 7 filter tests, graph artifact 100 nodes /
463 edges.

## Phases

### Arc 0 — Baseline & design
- **W1** Baseline freeze + this ledger.
- **W2** Token bridge: iframe uses the shared concept tokens (severity aliases,
  type scale, spacing) without layout change.
- **W3** Iframe chrome → shared primitives (`gp-btn`, `gp-filter`, `gp-sev`,
  panel styles) while preserving ids/classes.
- **W4** Fluid iframe height in the parent + integration polish.

### Arc 1 — Honest encoding
- **W5** Truthful legend: remove false action-arrow/color claims; legend matches
  the live renderer.
- **W6** All 8 canonical node kinds get mapped colors.
- **W7** Edge encoding: distinguish co-mention vs action relationships; width by
  weight/evidenceCount; reduce single-blue dominance.
- **W8** Severity/importance derived only from real fields.
- **W9** Stats honesty: counts by period, cap disclosure, stale-age indicator.

### Arc 2 — Filtering & search
- **W10** Debounced search; camera/selection preserved.
- **W11** Relationship-type filter.
- **W12** Evidence-text search.
- **W13** Zero-result category states with real counts.
- **W14** Ranked/autocomplete node-select.
- **W15** Date scrubber beyond presets.

### Arc 3 — Inspection & navigation
- **W16** Drawer dialog semantics, focus trap, labelled title.
- **W17** Relation cards: direction, types, confidence, event IDs.
- **W18** Evidence cards: source, date, independence; honest empty states.
- **W19** Per-edge method/provenance text.
- **W20** Path tracing between selected nodes.
- **W21** Isolate/focus mode + back to result set.
- **W22** Device-local pin/compare.

### Arc 4 — Interaction & controls
- **W23** Keyboard node traversal + Enter inspect + Esc close.
- **W24** Reduced-motion inside the iframe.
- **W25** Edge hover/inspection tooltips.
- **W26** Camera reset/zoom-to-selection.
- **W27** Label toggle state sync + initial aria-pressed.
- **W28** Control ARIA + touch targets.

### Arc 5 — Performance
- **W29** Remove the runtime eager override; restore the lazy contract honestly.
- **W30** Runtime node/edge budget + disclosure when capped.
- **W31** Pause engine off-screen/hidden; adaptive particles/labels.
- **W32** Fetch caching + snapshot-fallback duplication reduction.
- **W33** FPS tier + `webglcontextlost` handling.
- **W34** Action-overlay churn, toggle, label collisions.

### Arc 6 — Cross-surface integration
- **W35** Iframe ↔ parent selection via postMessage.
- **W36** Detail cross-links to Map/Brain/Search.
- **W37** Dashboard explorer sort/paging + honest category states.
- **W38** Brain overlay gating + relationship caveat.

### Arc 7 — Quality & acceptance
- **W39** Accessibility + honesty audit, including doc drift.
- **W40** Full regression + docs.

## Decision log
- 2026-09-10 — Target: same concept design language + depth; no mockups.
- 2026-09-10 — Naming: W1–W40; Map continues M5–M44.
- 2026-09-10 — Order: Web first, then Map.
- 2026-09-10 — Branch: `intelweb-concept-track` stacked on `gui-concept-track`.
