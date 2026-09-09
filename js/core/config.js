/** Global Pulse configuration */

export const CONFIG = {
  endpoints: {
    snapshot: './data/snapshot.json',
    liveArticles: './data/live_articles.json',
    intelligenceGraph: './data/intelligence_graph.json',
    intelligenceBrain: './data/intelligence_brain.json',
    sources: './data/sources.json',
    sourceHealth: './data/source_health.json',
    refreshManifest: './data/refresh_manifest.json',
    validationResults: './data/validation_results.json',
    pipelineHistory: './data/pipeline_history.json',
    liveStatus: './data/live_status.json',
    mapEvents: './data/live_events.json',
    mapRegional: './data/regional_intelligence.json',
    mapCartel: './data/enforcer_maps.json',
    mapLinks: './data/map_event_links.json',
    mapPoints: './data/map_points.json',
    whatChanged: './data/what_changed.json',
    eventHistory: './data/event_history.json',
    historicalTrends: './data/historical_trends.json',
    intelligenceBrief: './data/intelligence_brief.json'
  },
  fetch: {
    timeoutMs: 15000,
    snapshotTimeoutMs: 25000,
    retries: 1,
    retryDelayMs: 400
  },
  refresh: {
    snapshot: 5 * 60 * 1000,
    breaking: 10 * 60 * 1000,
    markets: 15 * 60 * 1000,
    map: 5 * 60 * 1000
  },
  confidence: {
    high: 0.75,
    moderate: 0.5,
    limited: 0.3
  },
  maxBreakingItems: 12,
  maxConflictCards: 8,
  mapDefaultCenter: [20, 10],
  mapDefaultZoom: 2
};

export const CONFIDENCE_LABELS = {
  high: { label: 'CONFIRMED', class: 'conf-high' },
  moderate: { label: 'LIKELY', class: 'conf-mod' },
  limited: { label: 'LIMITED', class: 'conf-low' },
  unverified: { label: 'UNVERIFIED', class: 'conf-unver' },
  conflicting: { label: 'CONFLICTING', class: 'conf-conflict' }
};
