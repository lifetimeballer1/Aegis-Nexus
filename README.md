# Aegis Nexus

**Evidence-backed global intelligence platform for conflict, geopolitical risk, public-source reporting, disasters, organized crime, strategic nodes, markets, and cross-domain intelligence relationships.**

Aegis Nexus is a public-source intelligence monitor. It does not claim classified access and it does not intentionally collect visitor identities or precise visitor locations.

## Architecture

```text
Public sources
  ↓
Ingestion + source health
  ↓
Normalization + timestamp handling
  ↓
Failover / preservation
  ↓
Conflict + OSINT + hazard + market + macro enrichment
  ↓
Events + claims + assessments + historical artifacts
  ↓
Evidence-linked Intelligence Web
  ↓
Cross-domain Intelligence Brain
  ↓
Canonical JSON artifacts + refresh manifest
  ↓
GitHub Pages
  ↓
Aegis Nexus dashboard / map / markets / Brain / Intelligence Web
```

`refresh_pipeline.py` is the canonical refresh orchestrator used by GitHub Actions. The repository is intentionally a static production site: ingestion and processing happen in CI, while the browser consumes the resulting canonical JSON artifacts.

## Intelligence Web

The Intelligence Web is a WebGL-based 3D relationship graph backed by `data/intelligence_graph.json`. It is a presentation layer over source-backed intelligence, not an independent or manually populated database.

The renderer normalizes graph records, rejects duplicate IDs and invalid endpoints, preserves evidence, calculates node importance/connectivity/recency, and provides camera and inspection controls. It supports selection, hover labels, search, domain/time filters, relationship visibility, camera controls, mobile interaction, and explicit loading/error states.

Relationships represent contextual public evidence connecting records. They do **not** prove causation, coordination, intent, or responsibility.

## Intelligence Brain

`data/intelligence_brain.json` is the compact cross-domain graph used by the main Brain experience. It is rebuilt from source-backed artifacts including live news, conflict data, OSINT/map signals, event intelligence, claims, assessments, market context, macro data, and the canonical Intelligence Web graph.

The current production contract permits **up to 35 major nodes**. Raw evidence remains upstream and is consolidated beneath human-readable hubs. Validation requires canonical nodes, valid coordinates where applicable, unique relationships, non-empty evidence, and consistent statistics.

## Data pipeline

The canonical pipeline includes:

- live RSS/Atom news collection with persistent SQLite storage
- feed registry rebuild from the canonical catalog
- source health and fallback processing
- failover-state refresh from collector telemetry (retention-based; no stories merged)
- conflict corroboration from UCDP/CFR/public reporting
- OSINT and geographic layers
- GDACS disaster alerts and USGS earthquakes
- strategic and chokepoint layers
- market data and session/freshness handling
- World Bank macro context
- event history/intelligence/consistency/resolution/market impact
- claims and intelligence assessments
- historical trend calculations
- evidence-linked Intelligence Web generation
- compact Intelligence Brain generation and validation
- canonical map marker generation
- structured validation-results recording
- pipeline run-history recording
- refresh manifest/hash verification

A failure in an optional external source is handled through source-health/failover logic rather than automatically destroying the entire dataset. Internal validation failures remain fail-closed so partially processed artifacts are not silently published.

## Canonical artifacts

Core generated files include:

- `data/snapshot.json` — primary dashboard state
- `data/history.json` — historical state
- `data/sources.json` — source registry (rebuilt every refresh from the canonical catalog)
- `data/live_articles.json` — normalized live-news export
- `data/live_status.json` — source health/collector telemetry
- `data/intelligence_graph.json` — canonical evidence-linked Intelligence Web graph
- `data/intelligence_brain.json` — compact cross-domain Brain
- `data/map_points.json` — validated browser map feed
- `data/validation_results.json` — per-contract validation outcomes with evidence tails
- `data/pipeline_history.json` — recent refresh run records (trigger, duration, status)
- `data/refresh_manifest.json` — generation metadata and hashes (covers the pipeline-written feed, graph, Brain, map, health, and registry artifacts)

Additional event, assessment, claim, market-impact, trend, regional, and OSINT artifacts are produced by the pipeline.

## Map

The canonical map is implemented in `js/modules/map.js` with Leaflet on a dark Esri canvas basemap (OpenStreetMap fallback). It consumes the generated `data/map_points.json` feed and supports conflict, hazard, strategic, cartel/organized-crime and OSINT layers, clustering, filters, search, marker details, reset/fit controls, source links, and Brain relationship lines.

The pipeline validates geographic coordinates before publication, and the browser filters malformed coordinates defensively before creating markers.

## Dashboard

The main dashboard exposes:

- global situation overview
- breaking/latest public reporting
- active conflict watch
- Intelligence Brain
- Intelligence Web
- global situation map
- market context
- source/system health

Displayed data is sourced from the canonical generated artifacts. Loading, empty, stale, and error states are explicit rather than replaced with fabricated values.

## Analyst workspace

Beyond the read-only intelligence picture, the browser offers device-local analyst tools. Everything in this section stores data only in the visitor's own browser (localStorage) or exports a local file. There are no accounts, no team backends, no delivery integrations, and no generated content:

- alert queue with severity filters, evidence expansion, and acknowledgement (with an acknowledgement status table)
- event timeline with 24H/7D/30D/ALL presets plus a custom date range
- briefing drafts: title/type/classification/priority, executive summary, key judgments, supporting content (alert links and pasted source URLs only), analyst notes, and JSON export
- universal search across stories, conflicts, events, Brain, Web, map, and brief records (`Ctrl+K` or `/` jumps to it)
- saved views: named snapshots of alert/timeline/brief filters, applied back through each module's own renderer
- My Watchlist: pinned entities resolved against the current pipeline brief watchlist, with JSON export
- settings: auto-refresh cadence, per-store device-data clearing, and build/about facts from canonical state

Drafts, pins, acknowledgements, and views are the analyst's own work product. The application never generates assessments on their behalf.

## Refresh and deployment

The canonical GitHub Actions workflow is `.github/workflows/update-snapshot.yml`.

It performs the production refresh, source failover, map generation, intelligence graph generation, Brain generation/validation, regression and operational checks, generated-artifact verification, commit verification, and GitHub Pages deployment.

The workflow is scheduled and also supports manual execution. Deployment is intentionally blocked when required internal validation fails.

## Validation

Important repository gates include:

- source health
- data resilience/failover
- map coordinate validation
- market validation
- event pipeline validation
- Intelligence Web evidence validation
- Intelligence Brain validation
- repository integrity
- browser security/privacy checks
- performance/mobile invariants
- operational health
- generated-artifact/hash verification
- structured per-contract validation results (`data/validation_results.json`) and run history (`data/pipeline_history.json`), both rendered in Sources / Validation / System Health

A green syntax/build check alone is not considered proof that the intelligence system is healthy.

## Browser architecture

The application is a mobile-first static site with modular JavaScript under `js/` plus focused browser modules.

Key layers include:

- `js/core/` — application state/configuration/utilities
- `js/modules/` — feature and map modules
- `global_pulse_core.js` — dashboard integration
- `global_pulse_event_pipeline.js` — event integration
- `global_pulse_brain_ui.js` — Brain presentation
- `global_pulse_performance.js` — deferred/mobile performance behavior
- `global_pulse_qa.js` — browser QA hardening
- `intelligence_web_v2.js` — live 3D Intelligence Web renderer (loaded by `intelligence-web.html`; data from `data/intelligence_graph.json` with `data/intelligence_brain.json` layered in by the parent explorer)
- `intelligence_brain_web.js` — retired renderer kept only for historical reference; not loaded by any page
- `intelligence_web_controls_fix.js` — Intelligence Web controls behavior

The `global_pulse_*` filenames are retained as internal compatibility identifiers; they are not the application brand. The public application identity is Aegis Nexus.

## Security and privacy

The production browser uses CSP and strict browser security headers. External source text is escaped before DOM insertion. Visitor identity/fingerprinting and client-side ingestion credentials are not part of the application model.

Workflow permissions are limited to what the deployment requires. Third-party actions are currently major-version pinned; immutable SHA pinning remains a future hardening opportunity.

See `SECURITY.md` and `PRIVACY.md`.

## Local development

Serve the site over HTTP so browser modules and JSON artifacts behave like production:

```bash
python -m http.server 8000
```

Open `http://localhost:8000`.

To execute the canonical data refresh locally:

```bash
python refresh_pipeline.py
```

The refresh requires network access to its public sources and currently targets Python 3.12 in CI.

## Tests

Run the regression suite with:

```bash
python -m pytest -q
```

Useful validation commands include:

```bash
python validate_data_resilience.py
python validate_intelligence_brain.py
python validate_performance.py
python validate_operational_health.py
python validate_security.py
python validate_repository.py
node --test tests/intelligence_web_filters.test.cjs
```

## Production limitations

Aegis Nexus depends on public third-party feeds. Publishers, APIs, rate limits, timestamps, geographic coverage, and availability can change without notice.

Market information is contextual public data, not a trading/execution service. The Intelligence Web and Brain are structured evidence-linking systems and should not be interpreted as proof of hidden relationships or causation.

## Rebrand

The public product identity is **Aegis Nexus**. User-facing branding and PWA metadata use Aegis Nexus. Existing internal `global_pulse_*` implementation names are retained where changing them would add unnecessary compatibility risk; they are implementation identifiers rather than user-facing branding.

## Maintenance rule

Extend the canonical pipeline and renderers rather than adding parallel rescue/experimental implementations. Remove obsolete code only after confirming it is not referenced by the live site or CI. Documentation must remain synchronized with the actual implementation.
