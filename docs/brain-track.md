# Aegis Nexus — Brain Track (B1–B40)

Site-wide intelligence fusion: stories, gap detection with refresh-driven
closure, brain-fused Global Tension v6, and the Intelligence Web as the
explainer of how the Brain works.

## Scope and invariants

- **Pipeline changes are in scope** (unlike C/W/M): `build_*.py`,
  `refresh_pipeline.py`, validators, workflows — still **no fabricated data**.
- Every gap and story must cite canonical evidence. No invented entities,
  events, or numbers. Missing data renders honestly.
- All existing contracts preserved: Brain flags/`maxNodes=35`/kinds, manifest
  hashes, JS strings, browser smoke, action-intelligence gates.
- One writer per artifact. `scoreVersion` bumps are documented.
- New artifacts are added to REQUIRED/MANIFEST with fail-closed validators.

## Verification per phase

`python -m pytest -q` (116 baseline) + `node --test tests/intelligence_web_filters.test.cjs`
+ relevant validators; pipeline phases run targeted builders and validators
locally; UI phases run `tests/dashboard_smoke.py` desktop/mobile.

Baseline at B1: branch `brain-track` off `map-concept-track`, brain 28 nodes /
94 edges, tension 41 stale (freshness 2026-09-06), 116 pytest passing.

## Phases

### Arc 0 — Truth & contracts
- **B1** Baseline freeze + this ledger.
- **B2** Kill the stale-timestamp rewrite in `ensure_brain_groups.py`; record
  honest tension freshness.
- **B3** Story/Gap/Completeness schema (new `brain_schema.py`).
- **B4** Fail-closed validators for `brain_stories.json` and
  `brain_gap_history.json`.
- **B5** Pipeline wiring map + stage-order tests for new stages.

### Arc 1 — Rebuild dormant layers
- **B6** Wire `build_live_events.py` into the canonical refresh.
- **B7** Wire `claim_intelligence.py` + `build_source_evidence.py`.
- **B8** Wire `build_event_intelligence.py` + `build_event_consistency.py`.
- **B9** Wire `build_event_resolution.py`.
- **B10** Wire `build_intelligence_assessment.py`.
- **B11** Wire `build_historical_trends.py` (after tension).
- **B12** Validator/test catch-up; no empty-layer passes.

### Arc 2 — Story fusion engine
- **B13** Story identity from canonical events + live events (dedupe via
  resolution).
- **B14** Evidence independence/corroboration per story.
- **B15** Story slots + completeness scoring.
- **B16** Gap detectors (no_target, single_source, no_primary, no_geo, stale,
  contradiction, unresolved_duplicate, no_assessment).
- **B17** Gap lifecycle + `brain_gap_history.json`.
- **B18** Story ranking (severity × corroboration × recency × gap urgency).
- **B19** Publish `brain_stories.json` (caps + provenance refs) + manifest.
- **B20** Builder tests (fusion, gaps, no fabrication).

### Arc 3 — Tension v6
- **B21** v6 spec + audit fields.
- **B22** Single-writer tension stage before manifest; `scoreVersion=6`.
- **B23** Story-pressure contribution (closures lower it; capped).
- **B24** Unify thresholds/early-warning; delete dead legacy UIs.
- **B25** Tension audit payload (top contributing stories).
- **B26** Tension validators/tests + method docs.

### Arc 4 — Brain workspace
- **B27** "What matters now" ranked story feed.
- **B28** Story cards (actors/targets/timeline/confidence/gaps/contribution).
- **B29** Gap board (age, closure progress, "filled in" deltas).
- **B30** Refresh delta strip (new/updated/closed).
- **B31** Story timeline + hub drilldown aggregation.
- **B32** Surface actionLayer + cross-links (Map/Web/Timeline/Alerts/Briefings).

### Arc 5 — Web explainer
- **B33** Brain mode: story subgraph overlay.
- **B34** Gap ghost nodes.
- **B35** Provenance paths evidence→story→hub→tension + "Explain this".
- **B36** Typed canonical relationships replace co-mention-only edges.
- **B37** Gap/severity/hub filtering + a11y.

### Arc 6 — Acceptance
- **B38** Dashboard integration (story/tension tiles) + honesty/a11y audit.
- **B39** Local pipeline dry-run + validators + smoke extensions + payload budgets.
- **B40** Docs, acceptance evidence, PR + local preview.

## Decision log
- 2026-09-10 — Tension should be higher than the stale 41 when real critical
  stories are open; v6 makes that auditable.
- 2026-09-10 — Story = canonical event cluster.
- 2026-09-10 — Dormant event/claim layers are rewired into the refresh.
- 2026-09-10 — New manifest-hashed artifacts: `brain_stories.json`,
  `brain_gap_history.json`.
- 2026-09-10 — Deterministic evidence rules only; no LLM/backend, no fabrication.
