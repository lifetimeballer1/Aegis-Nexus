# Global Pulse Intelligence Architecture

## Mission
Global Pulse is a public, evidence-oriented global intelligence monitor. It is designed to summarize public information, expose uncertainty, preserve source provenance, and help users investigate events. It does not claim access to classified information and it does not identify or track visitors.

## Canonical data flow

`public reports -> normalization -> candidate claims -> evidence linkage -> corroboration/contradiction -> events -> entities/relationships -> assessments -> cross-domain Intelligence Brain -> UI`

### Intelligence Brain

The Intelligence Brain is the cross-domain relationship layer. Each refresh rebuilds `data/intelligence_brain.json` from the current public intelligence artifacts rather than maintaining a separate hidden database. It connects, where supported by the available evidence/context:

- live news and source records
- conflicts and corroboration layers
- geographic/map signals
- event intelligence and historical context
- claims and assessments
- market indicators and macro context
- the evidence-linked Intelligence Web

The brain is time-aware at the artifact level and preserves evidence links when available. Market relationships are explicitly contextual relevance mappings and are never presented as causal proof. The browser can select a node and trace its connected signals and supporting source.

### Evidence rules

1. Report count is never treated as truth.
2. A distinct domain is not automatically an independent source.
3. Syndicated, copied, or clearly derivative reports should not increase independent-evidence counts.
4. Contradicting or denying reports remain attached to the claim.
5. Confidence must be explainable from observable factors.
6. Every intelligence relationship should retain evidence/provenance where available.
7. Missing data is represented as missing; the system must not manufacture precision.
8. Public-source collection must not collect visitor identifiers or precise user location.

## Reliability model

The system distinguishes:

- **Source domain** — the web publisher/domain.
- **Source family** — the underlying publisher/network when known.
- **Report** — one published item.
- **Claim** — a normalized proposition suggested by one or more reports.
- **Event** — a time/location/topic cluster of related claims.
- **Entity** — a country, organization, person, place, infrastructure item, or other durable object.
- **Assessment** — an explicitly qualified interpretation based on evidence.

## Intelligence Web rendering architecture

`data/intelligence_graph.json` is the canonical source for the Intelligence Web presentation. The browser renderer is a presentation layer and does not create a competing intelligence database.

```text
data/intelligence_graph.json
        ↓
validated normalization
        ↓
node + relationship scoring
        ↓
3D force-directed layout
        ↓
Three.js / WebGL renderer
        ↓
interaction + filters + camera
        ↓
selected-node intelligence inspector
```

`intelligence_web_v2.js` (loaded by `intelligence-web.html`) owns graph normalization, evidence filtering, kind and relationship color mapping, node sizing, force layout, WebGL rendering, hover/selection behavior, camera controls, filtering, path tracing, isolate/pin, and source inspection. The page uses `3d-force-graph` as the rendering engine. `intelligence_brain_web.js` is a retired renderer that is no longer loaded by any page.

Node size is derived from available real graph properties including degree/connectivity, mentions, importance/significance and confidence. Node color is controlled by the centralized `INTELLIGENCE_NODE_COLORS` mapping. Relationship appearance is based on relationship semantics and weight. Recent records receive greater visual emphasis without altering their source timestamps.

The renderer validates IDs, endpoints, duplicate records, evidence presence and optional fields before rendering. Empty-evidence nodes/edges are rejected. A pathological graph is bounded to 5,000 nodes after prioritizing connectivity/importance; this is a rendering safety limit, not a replacement for the upstream intelligence dataset.

The force simulation warms during layout, cools after stabilization, and is reheated when filters or refreshed graph data require a new layout. Node positions are retained by ID when possible so a refresh evolves the existing network instead of resetting every node.

The visual design is intentionally dark, dense and atmospheric: high-value hubs are larger/brighter, domain colors communicate meaning, relationship lines remain subtle, and labels are shown on demand rather than as a permanent DOM layer for every record.

Mobile behavior relies on the WebGL canvas and graph controls for touch rotation, pan and pinch zoom. The selected-node inspector becomes a bottom-sheet-style compact panel on small screens. If the WebGL dependency cannot load or the canonical artifact is unavailable, the page exposes an explicit failure/data-unavailable state and never generates fake intelligence.

## Current canonical refresh

`refresh_pipeline.py` is the production orchestrator. It refreshes live news, the market layer, political/OSINT/conflict/hazard layers, UCDP corroboration, World Bank macro context, event artifacts, the evidence-linked Intelligence Web, assessments, claims, What Changed, historical trends, and the cross-domain Intelligence Brain. It then cleans the generated index, applies browser security hardening, installs the browser QA layer, validates the repository, and writes `data/refresh_manifest.json` with SHA-256 hashes and freshness timestamps for critical generated artifacts.

Required public artifacts include `snapshot.json`, `history.json`, `sources.json`, `live_articles.json`, `intelligence_graph.json`, and `intelligence_brain.json`. The pipeline treats stale/missing required data as a validation failure rather than manufacturing replacement values.

## Market and external-data model

The market layer uses public Yahoo Finance chart data without a user API key. A refresh is accepted only when the market artifact is fresh, contains at least the expected indicator count, and includes positive real prices. Event-to-market relationships are contextual relevance mappings; they do not claim causation. The main dashboard exposes a compact market pulse so market context is visible without leaving the main page.

Open hazard, conflict-corroboration, and macro layers use keyless public sources such as GDACS/USGS, UCDP Candidate Events, and World Bank data. Source availability is recorded rather than treated as guaranteed.

## Browser resilience

The dashboard labels stale data, surfaces source failover health, shows a distinct snapshot-fetch failure state, and isolates map/graph rendering errors. Map markers expose keyboard/assistive labels, long evidence text is collapsible, and confidence is represented independently from signal color.

The Intelligence Brain and market pulse load their generated artifacts with cache-busting and fail safely if those artifacts are unavailable. The first-use guide explains signal colors and confidence tiers. Event/node cards can be deep-linked with URL hashes. Watchlists remain local to the browser.

## Security model

- Least-privilege GitHub Actions permissions.
- No secrets or API keys in browser code.
- No `pull_request_target` workflows.
- Automated privacy/security checks run before deployment.
- Third-party Actions should be reviewed and pinned to immutable commit SHAs where practical.
- Browser-facing HTML receives a defense-in-depth CSP; GitHub Pages itself controls the final HTTP response headers.
- External source content is escaped before insertion into the DOM.

## Maintenance rule

Do not add another versioned renderer (`v28`, `v29`, etc.) when an existing canonical module can be extended safely. New features should either extend the canonical implementation or document why a separate module is required. Deprecated installers and renderers should be removed only after confirming they are no longer referenced by workflows or the live site.
