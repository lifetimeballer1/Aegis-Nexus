# Aegis Nexus — GUI Concept Track (C1–C40)

Front-end-only track bringing the browser UI to **feature parity** with the three
reference mockups (Concept 01 Command Center, Concept 05 Briefings/Alerts/Timeline,
Concept 06 Sources/Validation/System Health), adapted to the data the canonical
pipeline actually publishes.

## Scope and invariants

- **Front-end only.** No changes to Python pipeline scripts, GitHub Actions
  workflows, or generated `data/*.json`. Data gaps are handled honestly in the UI.
- **Never fabricate.** No mock intelligence, fake sources, or invented metrics.
- **Preserve existing contracts.** DOM ids, section ids, script tags, severity
  tokens, and forbidden strings asserted by `tests/` remain valid.
- **Omitted mockup panels (unfakeable / test-forbidden):** Delivery Channels,
  Severity Routing, Team Watchlist, "Generate with AI", org-wide acknowledgement.
- **Semantic color:** blue = informational, amber = watch, red = critical,
  green = healthy. Severity color is never decorative.
- **GitHub Pages:** everything must work under the `/Aegis-Nexus/` subpath.

## Verification per phase

1. `python -m pytest -q` → no regressions (baseline 116).
2. `node --test tests/intelligence_web_filters.test.cjs` → passing.
3. Browser/runtime check where available (Playwright desktop 1440 + mobile 390).
4. Report changed files, tests, and browser verification explicitly.

Baseline at C1: `116 passed`, branch `gui-concept-track`, base `8a8891d`.

## Phases

### Arc 0 — Baseline & design system
- **C1** Baseline freeze + this ledger.
- **C2** Design-system reconciliation (`css/concept.css`) without regressions.
- **C3** UI primitives: tile, table, severity chip, donut, steps, drawer.

### Arc A — App shell & navigation
- **C4** Left icon rail (desktop), preserving `.gp-nav-item` count ≥ 18.
- **C5** Top command bar: tagline, inline search, alert badge, analyst chip.
- **C6** Responsive strategy: rail desktop / bottom nav mobile.
- **C7** View controller: hash deep links preserved; off-screen work reduced.
- **C8** Global search wiring (Ctrl/Cmd+K → existing module).

### Arc B — Command Center (Concept 01)
- **C9** KPI tiles with sparkline/delta/tone.
- **C10** Headline Intelligence feed with badges + honest thumbnail placeholder.
- **C11** Region event bubbles from `map_points.json`.
- **C12** Priority Regions table (sortable).
- **C13** "What Changed" using existing `what_changed.json` fields only.
- **C14** Market Pulse strip from symbols present in `snapshot.json`.
- **C15** Source Health donut (4 slices) + Recent Issues list.
- **C16** Dashboard assembly + visual QA.

### Arc C — Alerts (Concept 05)
- **C17** Severity filter tabs with live counts.
- **C18** Alert card component.
- **C19** Shared reading pane / detail drawer.
- **C20** Acknowledgement status table + device-only label.

### Arc D — Briefing Builder (Concept 05)
- **C21** Step wizard shell (Content/Structure/Review/Publish).
- **C22** Step 1 Content + counters.
- **C23** Step 2 Structure (judgments, supporting content).
- **C24** Step 3 Review + validation.
- **C25** Step 4 local export only.
- **C26** Brief integration + My Watchlist.

### Arc E — Timeline (Concept 05)
- **C27** Timeline axis restyle.
- **C28** Presets + event detail drawer.
- **C29** Cross-linking timeline ↔ alerts ↔ map/Brain.

### Arc F — Sources / Validation / System Health (Concept 06)
- **C30** KPI tiles (sources, pass rate, issues, pipeline time, integrity).
- **C31** Source Registry table.
- **C32** Validation & Data Contracts + blocked count + results table.
- **C33** Pipeline Run History incl. Workflow column.
- **C34** Refresh Pipeline Health flow.
- **C35** Artifact Integrity & Provenance.
- **C36** Settings & Governance thresholds.

### Arc G — Quality & acceptance
- **C37** Search + Saved Views polish.
- **C38** Mobile + performance.
- **C39** Accessibility + honesty audit.
- **C40** Regression + acceptance.

## Decision log
- 2026-09-10 — Fidelity: feature parity adapted to real data.
- 2026-09-10 — Forbidden mockup features omitted.
- 2026-09-10 — Target: `Default Project` `main`, branch `gui-concept-track`, C1–C40.
- 2026-09-10 — Scope: GUI only; C13/C14 do not touch the pipeline.
