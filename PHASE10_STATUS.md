# Phase 10 — Production polish and final intelligence quality

Local acceptance completed September 8, 2026, against base `56ccd105c2c5401de8b561f26eb324a2230a522c`. Production acceptance completed September 9, 2026: commit `1981de3` (duplicate-evidence folding) passed the scheduled production refresh (#656), browser smoke tests, and Pages deployment. GUI Phases 1-9 and Map M1-M4 are complete; GUI-10 consolidation (shared severity, token alias) in progress.

## Repairs

- Intelligence Web categories follow canonical entity kinds; search retains direct evidence connections. Time ranges filter source publication dates and exclude undated/future records. Selection, evidence drawers, relationship visibility, reset, and viewport resizing work on desktop/mobile.
- Database cache misses restore valid retained articles from the published export without changing source dates or reporting them as fresh feed successes.
- Pipeline validation reads `data/snapshot.json` and the browser's canonical `data/map_points.json`. The downstream workflow follows the canonical refresh name. Live monitoring targets `/Aegis-Nexus/`.
- Generated JSON keeps LF line endings so Windows checkout does not invalidate byte hashes. No intelligence artifacts were replaced or fabricated.
- CI runs all Python tests and the graph filter tests. Browser smoke tests exercise the actual `/Aegis-Nexus/` subpath and include Brain interactions.

## Acceptance evidence

- 37 Python tests and 7 JavaScript filter tests passed; workflow YAML, syntax, repository integrity, canonical schema, graph, action evidence, resilience/manifest, security, and performance checks passed.
- Real Edge/Chromium desktop (1440×900) and mobile (390×844) tests passed for map, Brain, lazy Web, search, filters, evidence drawers, empty/reset states, relationships, refresh, resize, and missing-renderer retry behavior. WebGL rendered 100 nodes / 403 edges without errors on the committed source-backed dataset.
- An isolated live canonical refresh restored 1,674 retained articles and added 165 new articles. It passed with 57/65 healthy source results, 1,839 articles, 100 graph nodes / 435 edges, 28 Brain nodes / 91 edges, and 2,880 map points. U.S. and China retained 11 and 1 explicitly targeted canonical events respectively. Operational health and manifest hashes passed.

## Production acceptance (refresh #656)

- Production refresh #656 (September 9, 2026, on commit `1981de3`) succeeded: the canonical builder folded 150 duplicate evidence records (2,000 articles → 1,850 evidence), and all 12 validation contracts passed, including the source-health gate that the earlier refresh #634 had failed (30.8% healthy at the time). No thresholds were weakened.
- Browser smoke tests on `1981de3` passed and the Pages deployment succeeded.
- The duplicate-folding change keeps entity/relationship identity stable (194 entities, 433 relationships on the same input) while mention counts, relationship weights, and event tallies no longer inflate on feed-mirror variants or same-outlet re-issues.

## Remaining limitations

Public-source outages and underlying extraction ambiguity remain limitations; contextual relationships are not causal proof. Local source availability differs from GitHub Actions, so a green local run does not guarantee the next scheduled production refresh.
