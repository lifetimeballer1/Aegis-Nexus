# Pipeline enrichment — dashboard payloads (2026-09-10)

Branch: `pipeline/enrich-dashboard-payloads-20260910`
Base: `10740a8` (GUI pushed live, renders correctly, thin panels)

## Freshness evidence (pre-fix, read-only probes)

- `data/snapshot.json.updatedAt`: 2026-09-10T12:36:07Z (fresh)
- `data/snapshot.json.marketData.updatedAt`: 2026-09-06T15:38:23Z (**4 days stale**)
- `data/strategic_signals.json.generatedAt`: 2026-09-10T12:36:09Z, 2 signals, `actionCount: 0` each
- `data/intelligence_brain.json`: 28 nodes, US/China each 100 evidence + 8 grouped actions
- `data/what_changed.json.updatedAt`: 2026-09-10T12:36:47Z, `items: []`, summary all zero
- `data/live_events.json`: 80 events, newest `firstSeen` 2026-09-05 (>12h, outside 12h window)
- `data/pipeline_history.json`: Success runs at 12:36, 11:17, 10:15 UTC — scheduler alive
- `data/source_health.json`: 63 feeds, 57 online, 6 failed, 53 onlineWithData

Conclusion per verification skill §8: market staleness is a **wiring gap**
(`refresh_pipeline.py` verified market but never ran `update_market_data.py`),
not a scheduler death. What-changed emptiness is an honest **window mismatch**
(12h window vs 5-day-old clustered events), not a fetch failure.

## Fixes (one per commit, local only, no push)

1. `aad20bc` — `refresh_pipeline.py`: run `update_market_data.py` before the
   market gate with tolerant fallback (preserve last good `marketData` on
   Yahoo outage). Keeps `noApiKey: true`, `indicators >= 20`, real-price gate.
2. `39eb967` — `build_strategic_signals.py` (v2 → v3): handle the real
   dict-grouped `node['actions']` shape from `enrich_brain_actions.py`
   (previous list-only parse yielded `actionCount: 0`); add honest fields
   (`evidenceCount`, `categories`, `topTargets`, `lastEvidenceTime`,
   `actionEvidenceCount`) plus capped secondary signals (max 6, ≥10 evidence)
   from existing Brain hubs. Keeps `sourceBackedOnly`, US/China coverage.
3. `bedf502` — `build_what_changed.py` (v1 → v2): 12h primary window plus
   honest 7-day `recentFallback` events labeled as such; window string and
   `recentFallbackEvents` summary count make the fallback explicit. Empty
   stays honest when truly nothing in 7 days.

GUI files untouched (`css/`, `js/` off limits). No `artifacts/` changes.

## Remaining gaps = upstream feed outages (do not patch with fabrication)

- `GDELT — Western Hemisphere Counter-Cartel`: HTTP 429 Too Many Requests
- `X @NASA`, `X @WhiteHouse`, `X @POTUS`, `X @NATO`, `X @UN`:
  proxy challenge / whitelist responses
- Yahoo Finance (market): rate-limited at times; tolerant fallback preserves
  last good quotes with `stale`/`closed` session status — DELAYED badge stays honest.
- `live_events` clustering window: newest cluster 2026-09-05; needs fresher
  `snapshot.stories` ingestion (future work, not fabricated here).

## Verification (from repo root)

- `python validate_repository.py`
- `python validate_performance.py`
- `python validate_security.py`
- `python -m pytest -q`
