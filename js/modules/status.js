/** GUI Phase 6 — Sources / Validation / System Health workspace.
 * Every figure is read from the canonical source-health artifact
 * (data/source_health.json with summary/sources), collector telemetry
 * (data/live_status.json) and refresh-manifest hashes — never invented.
 * Source state uses the artifact's real fields (status online/failed,
 * consecutiveFailures, contentStatus, freshnessMinutes) — never invented.
 * Severity follows the shared language: green healthy, amber watch,
 * red critical. Missing data renders honest loading/empty states. */

import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

let statusFilter = 'all';
let statusQuery = '';
let showAllSources = false;

const SOURCE_PAGE = 12;

function isOnline(source) {
  return String(source?.status || '').toLowerCase() === 'online';
}

/* Credibility tier, derived transparently from real registry fields
 * (consecutiveFailures, rowsFetched, freshnessMinutes) — a presentation
 * rule, not a measured score. Rule shown in the row title attribute. */
function credibilityTier(source) {
  const fails = Number(source?.consecutiveFailures || 0);
  const rows = Number(source?.rowsFetched || 0);
  const fresh = Number(source?.freshnessMinutes);
  if (fails === 0 && rows > 0 && (!Number.isFinite(fresh) || fresh <= 180)) return 'High';
  if (fails <= 2 && rows > 0) return 'Medium';
  return 'Low';
}

function fallbackMode(source) {
  if (source?.mode) return String(source.mode);
  if (source?.fallbackAvailable) return 'standby available';
  return '—';
}

function sourceDetail(source) {
  const parts = [];
  if (source?.type || source?.category) parts.push(String(source.type || source.category));
  if (source?.contentStatus) parts.push(String(source.contentStatus).replace(/_/g, ' '));
  if (Number.isFinite(Number(source?.freshnessMinutes))) parts.push(`${Number(source.freshnessMinutes).toFixed(0)}m fresh`);
  const fails = Number(source?.consecutiveFailures || 0);
  if (fails > 0) parts.push(`${fails} consecutive failure${fails === 1 ? '' : 's'}`);
  return parts.join(' · ');
}

let registryQuery = '';
let registryFilter = 'attention';
let registryExpanded = false;

const REGISTRY_VISIBLE = 25;

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

function fmtInt(value) {
  return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : '—';
}

function fmtSize(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n < 0) return '—';
  if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${n} B`;
}

function sourceState(source) {
  const status = String(source.status || source.mode || '').toLowerCase();
  if (status === 'online' && String(source.contentStatus || '').toLowerCase().indexOf('unavailable') === -1 && Number(source.rowsFetched || 0) > 0) return 'healthy';
  if (status === 'failed' || status === 'error' || status === 'offline') return 'critical';
  return 'watch';
}

/* Device-local governance thresholds (Concept 06 Settings & Governance).
 * These only change how THIS browser highlights rows — they never alter
 * pipeline validation, which stays fail-closed server-side. */
const GOV_KEY = 'gp.govThresholds.v1';
function loadGov() {
  try {
    const raw = JSON.parse(localStorage.getItem(GOV_KEY) || '{}');
    return {
      sourceFailure: Number(raw.sourceFailure) > 0 ? Number(raw.sourceFailure) : 3,
      validationFailure: Number(raw.validationFailure) > 0 ? Number(raw.validationFailure) : 5,
      freshnessMinutes: Number(raw.freshnessMinutes) > 0 ? Number(raw.freshnessMinutes) : 60
    };
  } catch { return { sourceFailure: 3, validationFailure: 5, freshnessMinutes: 60 }; }
}
function saveGov(gov) {
  try { localStorage.setItem(GOV_KEY, JSON.stringify(gov)); } catch {}
}

function stateBadge(kind, label) {
  return `<span class="gp-sev gp-sev-${kind}">${esc(label)}</span>`;
}

function registryRows(list) {
  const gov = loadGov();
  return list.map(s => {
    const kind = sourceState(s);
    const label = kind === 'healthy' ? 'Online' : kind === 'critical' ? 'Failing' : 'Degraded';
    const fails = Number(s.consecutiveFailures || 0);
    const cred = credibilityTier(s);
    const credPct = cred === 'High' ? 92 : cred === 'Medium' ? 64 : 30;
    const fresh = Number.isFinite(Number(s.freshnessMinutes)) ? `${Number(s.freshnessMinutes).toFixed(0)}m` : '—';
    const stale = Number.isFinite(Number(s.freshnessMinutes)) && Number(s.freshnessMinutes) > gov.freshnessMinutes;
    return `<tr><td class="strong">${esc(s.name || s.url || 'Unnamed source')}</td>`
      + `<td>${esc(s.category || s.type || 'uncategorized')}</td>`
      + `<td${stale ? ' title="Older than the device freshness threshold"' : ''}>${esc(fresh)}${stale ? ' <span class="gp-sev sev-high">stale</span>' : ''}</td>`
      + `<td><span class="gp-dot ${esc(kind)}"></span> ${esc(label)}</td>`
      + `<td class="num">${fmtInt(fails)}</td>`
      + `<td><span class="gp-cred" title="Derived: no failures + fresh rows = High; ≤2 failures + rows = Medium; else Low"><span class="gp-cred-bar"><i style="width:${credPct}%"></i></span><span>${cred}</span></span></td>`
      + `<td>${esc(fallbackMode(s))}</td></tr>`;
  }).join('');
}

function renderRegistry(sources) {
  const box = document.getElementById('srcRegistry');
  if (!box) return;
  const q = registryQuery.trim().toLowerCase();
  let list = (sources || []).filter(s => s && typeof s === 'object');
  if (registryFilter !== 'all') list = list.filter(s => sourceState(s) !== 'healthy');
  if (q) {
    list = list.filter(s => `${s.name || ''} ${s.category || ''} ${s.type || ''} ${s.url || ''}`.toLowerCase().includes(q));
  }
  const ordered = [...list].sort((a, b) => {
    const rank = s => (sourceState(s) === 'critical' ? 0 : sourceState(s) === 'watch' ? 1 : 2);
    return rank(a) - rank(b) || String(a.name || '').localeCompare(String(b.name || ''));
  });
  const shown = registryExpanded ? ordered : ordered.slice(0, REGISTRY_VISIBLE);
  box.innerHTML = `<div class="gp-filter-row" role="group" aria-label="Source status filter">`
    + `<button class="gp-filter${registryFilter === 'attention' ? ' active' : ''}" data-src-filter="attention" type="button">Needs attention</button>`
    + `<button class="gp-filter${registryFilter === 'all' ? ' active' : ''}" data-src-filter="all" type="button">All sources (${(sources || []).length})</button></div>`
    + `<input id="srcSearch" class="gp-dash-search" type="search" aria-label="Filter sources" placeholder="Filter sources…" value="${esc(registryQuery)}">`
    + (shown.length ? `<div class="gp-table-wrap"><table class="gp-table" aria-label="Source registry"><thead><tr><th>Source</th><th>Category</th><th>Freshness</th><th>Status</th><th class="num">Failures</th><th>Credibility</th><th>Fallback Mode</th></tr></thead><tbody>${registryRows(shown)}</tbody></table></div><div class="meta" style="margin-top:6px;font-size:10px;color:var(--muted-2)">Showing ${shown.length} of ${ordered.length} matching sources</div>` : '<div class="gp-state"><div class="gp-state-title">No sources match</div><div>No registry entries match the current filter.</div></div>')
    + (ordered.length > REGISTRY_VISIBLE ? `<button id="srcMore" class="gp-btn gp-more" type="button">${registryExpanded ? 'Show fewer' : `Show all ${ordered.length}`}</button>` : '');
  box.querySelectorAll('[data-src-filter]').forEach(btn => btn.addEventListener('click', () => {
    registryFilter = btn.dataset.srcFilter; registryExpanded = false; renderRegistry(sources);
  }));
  document.getElementById('srcSearch')?.addEventListener('input', event => {
    registryQuery = event.target.value; registryExpanded = false;
    const pos = event.target.selectionStart;
    renderRegistry(sources);
    const again = document.getElementById('srcSearch');
    if (again) { again.focus(); try { again.setSelectionRange(pos, pos); } catch { /* keep focus only */ } }
  });
  document.getElementById('srcMore')?.addEventListener('click', () => { registryExpanded = !registryExpanded; renderRegistry(sources); });
}

export function renderStatus() {
  const el = document.getElementById('statusBody');
  if (!el) return;
  const { status, lastSuccessfulFetch, sourceHealth, liveStatus, refreshManifest, errors, validationResults, pipelineHistory, snapshot, intelligenceBrain } = getState();
  const stamp = document.getElementById('statusUpdated');

  if (!sourceHealth && !liveStatus && !refreshManifest && status === 'loading') {
    el.innerHTML = '<div class="gp-state"><div class="gp-spinner"></div><div>Loading source health…</div></div>';
    return;
  }

  let html = '';
  if (!sourceHealth) {
    html += '<div class="gp-state"><div class="gp-state-title">Source health unavailable</div><div>Health telemetry failed to load. Check fetch errors below.</div></div>';
  } else {
    const summary = sourceHealth.summary || {};
    const list = Array.isArray(sourceHealth) ? sourceHealth : (sourceHealth.sources || []);
    const total = Number(summary.total ?? list.length);
    const online = list.filter(isOnline);
    const failed = list.filter(s => !isOnline(s));
    const onlineWithData = Number(summary.onlineWithData ?? online.length);
    const failedCount = Number(summary.failed ?? failed.length);
    const pillSev = failedCount === 0 ? 'healthy' : (online.length ? 'watch' : 'critical');

    const visible = (statusFilter === 'online' ? online : statusFilter === 'failed' ? failed : list)
      .filter(s => !statusQuery || [s.name, s.id, s.domain, s.url, s.type, s.category].join(' ').toLowerCase().includes(statusQuery));
    const shown = showAllSources ? visible : visible.slice(0, SOURCE_PAGE);

    const chips = [
      `<button class="gp-filter${statusFilter === 'all' ? ' active' : ''}" data-status-filter="all" type="button">All (${list.length})</button>`,
      `<button class="gp-filter${statusFilter === 'online' ? ' active' : ''}" data-status-filter="online" type="button">Online (${online.length})</button>`,
      `<button class="gp-filter${statusFilter === 'failed' ? ' active' : ''}" data-status-filter="failed" type="button">Failed (${failed.length})</button>`
    ].join('');

    const rows = shown.map(s => {
      const ok = isOnline(s);
      const name = s.name || s.id || s.domain || 'Unnamed source';
      const age = s.lastSuccess || s.lastChecked || s.updatedAt;
      const fresh = Number.isFinite(Number(s.freshnessMinutes)) ? `${Number(s.freshnessMinutes).toFixed(0)}m ago` : '—';
      const fails = Number(s.consecutiveFailures || 0);
      return `<div class="gp-source-row sev-${ok ? 'healthy' : 'critical'}"><div class="grow"><div class="title">${escapeHtml(String(name))}</div>`
        + `<div class="meta">${escapeHtml(String(s.type || s.category || 'source'))} · fresh ${escapeHtml(fresh)} · ${escapeHtml(String(s.contentStatus || 'unknown').replace(/_/g, ' '))}${fails > 0 ? ` · ${fails} consecutive failure${fails === 1 ? '' : 's'}` : ''}${age ? ` · ${escapeHtml(formatRelativeTime(age))}` : ''}</div></div>`
        + (ok ? '<span class="gp-source-chip sev-healthy">Online</span>' : `<span class="gp-sev gp-sev-critical">Failed</span>`) + '</div>';
    }).join('');

    const coverage = Number(sourceHealth.summary?.dataCoveragePercent);
    const runsAll = Array.isArray(pipelineHistory?.runs) ? pipelineHistory.runs : [];
    const avgSec = runsAll.length ? runsAll.reduce((a, r) => a + (Number(r.durationSeconds) || 0), 0) / runsAll.length : NaN;
    const artifactList = refreshManifest?.artifacts && typeof refreshManifest.artifacts === 'object' ? Object.entries(refreshManifest.artifacts) : [];
    const vS = validationResults?.summary || {};
    const vRanN = Number(vS.run ?? (Array.isArray(validationResults?.results) ? validationResults.results.length : 0));
    const vPassN = Number(vS.passed ?? 0);
    const degradedN = Math.max(0, Number(summary.onlineEmpty ?? (online.length - onlineWithData)));
    const kpiStrip = `<div class="gp-tiles" role="list" aria-label="System health indicators" style="margin-bottom:10px">`
      + `<div class="gp-tile tone-blue" role="listitem"><span class="gp-tile-label">Active Sources</span><span class="gp-tile-value">${fmtInt(total)}</span><span class="gp-tile-sub">${fmtInt(online.length)} online · ${fmtInt(degradedN)} degraded</span></div>`
      + `<div class="gp-tile tone-green" role="listitem"><span class="gp-tile-label">Validation Pass Rate</span><span class="gp-tile-value">${vRanN > 0 ? `${Math.round(vPassN / vRanN * 100)}%` : '—'}</span><span class="gp-tile-sub">${fmtInt(vPassN)} of ${fmtInt(vRanN)} contracts</span></div>`
      + `<div class="gp-tile tone-red" role="listitem"><span class="gp-tile-label">Sources with Issues</span><span class="gp-tile-value">${fmtInt(failedCount)}</span><span class="gp-tile-sub">failed the last refresh</span></div>`
      + `<div class="gp-tile tone-amber" role="listitem"><span class="gp-tile-label">Avg Pipeline Time</span><span class="gp-tile-value">${Number.isFinite(avgSec) ? `${avgSec.toFixed(0)}s` : '—'}</span><span class="gp-tile-sub">${fmtInt(runsAll.length)} recorded runs</span></div>`
      + `<div class="gp-tile tone-blue" role="listitem"><span class="gp-tile-label">Artifact Integrity</span><span class="gp-tile-value">${fmtInt(artifactList.length)}</span><span class="gp-tile-sub">${Number.isFinite(coverage) ? `${coverage.toFixed(0)}% data coverage` : 'manifest-verified hashes'}</span></div></div>`;

    html += kpiStrip + `
    <div class="gp-card gp-source-summary sev-${pillSev}">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
        <div>
          <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">Overall Status</div>
          <div style="font-size:16px;font-weight:700">${failedCount === 0 ? 'All reporting sources online' : `${failedCount} source${failedCount === 1 ? '' : 's'} failing`}</div>
          <div style="font-size:11px;color:var(--muted-2);margin-top:2px">${total} tracked · ${onlineWithData} reporting with data · updated ${escapeHtml(formatRelativeTime(sourceHealth.updatedAt || lastSuccessfulFetch))}</div>
        </div>
        <div style="text-align:right;font-size:12px;color:var(--muted)">
          Last successful load<br>
          <strong>${escapeHtml(formatRelativeTime(lastSuccessfulFetch))}</strong>
        </div>
      </div>
    </div>
    <div class="gp-source-controls"><input id="statusSearch" class="gp-map-search" type="search" aria-label="Filter sources" placeholder="Filter sources…" value="${escapeHtml(statusQuery)}"></div>
    <div class="gp-filter-row" role="group" aria-label="Filter sources by state">${chips}`
      + `<span class="meta" style="align-self:center;font-size:10px;color:var(--muted-2)">Showing ${shown.length} of ${visible.length} sources</span></div>`
      + (rows || '<div class="gp-state"><div class="gp-state-title">No sources match</div><div>Nothing in the health registry matches this state or search.</div></div>')
      + (visible.length > SOURCE_PAGE ? `<button id="statusMore" class="gp-btn gp-more" type="button">${showAllSources ? 'Show fewer' : `Show all ${visible.length}`}</button>` : '');

    if (stamp) stamp.textContent = sourceHealth.updatedAt ? `Updated ${formatRelativeTime(sourceHealth.updatedAt)} · ${online.length}/${list.length} online` : '';
  }

  const live = liveStatus || {};
  const failedSources = Array.isArray(live.failedSources) ? live.failedSources : [];
  const manifest = refreshManifest || {};
  const artifacts = manifest.artifacts && typeof manifest.artifacts === 'object' ? Object.entries(manifest.artifacts) : [];
  const errorList = Object.entries(errors || {});

  const collector = live && live.updatedAt ? `
      <div class="gp-dash-grid">
        <div class="gp-dash-panel"><h3>Latest Collector Run</h3>
          <div class="gp-kpi-value" style="font-size:20px">${esc(formatRelativeTime(live.updatedAt))}</div>
          <div class="meta" style="font-size:10px;color:var(--muted-2)">${fmtInt(live.feedsChecked)} feeds checked · ${fmtInt(live.rowsFetched)} rows · ${fmtInt(live.newArticles)} new · ${fmtInt(live.exportedArticles)} exported</div></div>
        <div class="gp-dash-panel"><h3>Collector Health</h3>
          <div class="gp-kpi-value" style="font-size:20px;color:var(--sev-healthy)">${fmtInt(live.healthySources)}</div>
          <div class="meta" style="font-size:10px;color:var(--muted-2)">healthy · ${fmtInt(live.emptySources)} empty · ${fmtInt(failedSources.length)} failed</div></div>
      </div>
      ${failedSources.length ? `<div class="gp-dash-panel" style="margin-top:8px"><h3>Recent Collector Issues (${failedSources.length})</h3><div class="gp-dash-list">`
        + failedSources.slice(0, 5).map(f => `<div class="gp-dash-row"><div class="grow"><div class="title">${esc(f.source || 'Unnamed feed')}</div><div class="meta">${esc(String(f.error || 'unknown error').slice(0, 160))}</div></div></div>`).join('')
        + '</div></div>' : ''}` : '';

  const manifestBlock = artifacts.length ? `
      <div class="gp-panel" style="margin-top:8px"><div class="gp-panel-head"><h3 class="gp-panel-title">Artifact Integrity &amp; Provenance</h3><span class="gp-tiny gp-muted">${fmtInt(artifacts.length)} artifacts · ${esc(fmtSize(artifacts.reduce((a, [, m]) => a + (Number(m.size) || 0), 0)))} · generated ${esc(formatRelativeTime(manifest.generatedAt))}</span></div>
      <div class="gp-panel-body"><div class="gp-table-wrap"><table class="gp-table" aria-label="Artifact hashes"><thead><tr><th>Artifact</th><th>SHA-256</th><th class="num">Size</th></tr></thead><tbody>`
      + artifacts.map(([name, meta]) => `<tr><td class="strong gp-mono">${esc(name)}</td><td class="gp-mono">${esc(String(meta.sha256 || '').slice(0, 12))}…</td><td class="num">${esc(fmtSize(meta.size))}</td></tr>`).join('')
      + `</tbody></table></div><div class="gp-tiny gp-muted" style="margin-top:6px">Hash prefixes are read from the refresh manifest. A full provenance ledger is not published.</div></div></div>` : '';

  const vSummary = validationResults?.summary || {};
  const vResults = Array.isArray(validationResults?.results) ? validationResults.results : [];
  const vRan = Number(vSummary.run ?? vResults.length);
  const vPassed = Number(vSummary.passed ?? vResults.filter(r => r.passed).length);
  const vFailed = Number(vSummary.failed ?? vResults.filter(r => !r.passed).length);
  const vBlocked = Number(vSummary.blocked ?? 0);
  const validationBlock = `
      <div class="gp-panel" style="margin-top:8px"><div class="gp-panel-head"><h3 class="gp-panel-title">Validation &amp; Data Contracts</h3><span class="gp-tiny gp-muted">${fmtInt(vRan)} run · ${fmtInt(vPassed)} passed · ${fmtInt(vFailed)} failed · ${fmtInt(vBlocked)} blocked · recorded ${esc(formatRelativeTime(validationResults.updatedAt))}</span></div>
      <div class="gp-panel-body">${vResults.length ? `<div class="gp-table-wrap"><table class="gp-table" aria-label="Validation results"><thead><tr><th>Contract</th><th>Detail</th><th>Result</th></tr></thead><tbody>`
      + vResults.map(r => `<tr><td class="strong">${esc(r.contract || r.command || 'contract')}</td><td>${esc(String(r.detail || '').slice(0, 160))}</td><td>${r.passed ? '<span class="gp-sev sev-low">Passed</span>' : '<span class="gp-sev sev-critical">Failed</span>'}</td></tr>`).join('')
      + `</tbody></table></div>` : '<div class="gp-muted gp-tiny">No validation run recorded yet — published by the next pipeline refresh.</div>'}</div></div>`;

  const runs = Array.isArray(pipelineHistory?.runs) ? pipelineHistory.runs : [];
  const historyBlock = `
      <div class="gp-panel" style="margin-top:8px"><div class="gp-panel-head"><h3 class="gp-panel-title">Pipeline Run History</h3><span class="gp-tiny gp-muted">Workflow names are not published by the current pipeline</span></div>
      <div class="gp-panel-body">${runs.length ? `<div class="gp-table-wrap"><table class="gp-table" aria-label="Pipeline runs"><thead><tr><th>Run ID</th><th>Trigger</th><th>Started (UTC)</th><th class="num">Duration</th><th>Status</th></tr></thead><tbody>`
      + runs.slice(0, 8).map(r => {
        const ok = String(r.status || '').toLowerCase() === 'success';
        const dur = Number.isFinite(Number(r.durationSeconds)) ? `${Number(r.durationSeconds).toFixed(0)}s` : '—';
        const started = r.startedAt ? esc(String(r.startedAt).replace('T', ' ').slice(0, 19)) : '—';
        return `<tr><td class="strong gp-mono">${esc(String(r.runId || 'run').slice(0, 24))}</td><td>${esc(r.trigger || 'manual')}</td><td class="gp-mono">${started}</td><td class="num">${esc(dur)}</td><td>${ok ? '<span class="gp-sev sev-low">Success</span>' : '<span class="gp-sev sev-critical">Failed</span>'}</td></tr>`;
      }).join('')
      + `</tbody></table></div>` : '<div class="gp-muted gp-tiny">No run history yet — recorded on the next pipeline refresh.</div>'}</div></div>`;

  const snapStories = Array.isArray(snapshot?.stories) ? snapshot.stories.length : 0;
  const snapConflicts = Array.isArray(snapshot?.conflicts) ? snapshot.conflicts.length : 0;
  const brainNodes = Array.isArray(intelligenceBrain?.nodes) ? intelligenceBrain.nodes.length : 0;
  const brainEdges = Array.isArray(intelligenceBrain?.edges) ? intelligenceBrain.edges.length : 0;
  const flowNode = (label, value, sub, kind) => `<div class="gp-flow-node"><b>${label}</b><div class="gp-tile-value" style="font-size:18px;color:${kind === 'healthy' ? 'var(--green)' : kind === 'watch' ? 'var(--amber)' : kind === 'critical' ? 'var(--red)' : 'var(--text)'}">${value}</div><span>${sub}</span></div>`;
  const arrow = '<span class="gp-flow-arrow" aria-hidden="true">→</span>';
  const flowStrip = `
      <div class="gp-panel" style="margin-top:8px"><div class="gp-panel-head"><h3 class="gp-panel-title">Refresh Pipeline Health</h3><span class="gp-tiny gp-muted">Stage counts from canonical artifacts</span></div>
      <div class="gp-panel-body"><div class="gp-flow">`
      + flowNode('Ingest', live?.updatedAt ? `${fmtInt(live.feedsChecked)} feeds` : '—', live?.updatedAt ? `${fmtInt(live.rowsFetched)} rows · ${esc(formatRelativeTime(live.updatedAt))}` : 'no collector run', live?.updatedAt && Number(live.rowsFetched) > 0 ? 'healthy' : 'info')
      + arrow
      + flowNode('Validate', vResults.length ? `${fmtInt(vPassed)}/${fmtInt(vRan)}` : '—', vResults.length ? `gates passed${vFailed ? ` · ${fmtInt(vFailed)} failing` : ''}` : 'no validation run', !vResults.length ? 'info' : vFailed ? 'critical' : 'healthy')
      + arrow
      + flowNode('Transform', snapStories ? fmtInt(snapStories) : '—', snapStories ? `${fmtInt(snapConflicts)} conflicts normalized` : 'no snapshot', snapStories ? 'healthy' : 'info')
      + arrow
      + flowNode('Enrich', brainNodes ? fmtInt(brainNodes) : '—', brainNodes ? `${fmtInt(brainEdges)} brain edges` : 'no brain', brainNodes ? 'healthy' : 'info')
      + arrow
      + flowNode('Publish', artifacts.length ? fmtInt(artifacts.length) : '—', artifacts.length ? `artifacts · ${esc(formatRelativeTime(manifest.generatedAt))}` : 'no manifest', artifacts.length ? 'healthy' : 'info')
      + `</div></div></div>`;

  const gov = loadGov();
  const govBlock = `
      <div class="gp-panel" style="margin-top:8px"><div class="gp-panel-head"><h3 class="gp-panel-title">Settings &amp; Governance</h3><span class="gp-tiny gp-muted">Device-local view thresholds</span></div>
      <div class="gp-panel-body gp-stack">
        <div class="gp-grid gp-grid-3">
          <div class="gp-field"><label for="govSource">Source failures to flag</label><input id="govSource" class="gp-input" type="number" min="1" max="24" value="${gov.sourceFailure}"></div>
          <div class="gp-field"><label for="govValidation">Validation failures to flag</label><input id="govValidation" class="gp-input" type="number" min="1" max="24" value="${gov.validationFailure}"></div>
          <div class="gp-field"><label for="govFresh">Freshness threshold (min)</label><input id="govFresh" class="gp-input" type="number" min="5" max="1440" value="${gov.freshnessMinutes}"></div>
        </div>
        <div class="gp-row"><button class="gp-btn primary" id="govSave" type="button">Save thresholds</button><span class="gp-tiny gp-muted" id="govSaved">Only changes highlighting in this browser. Pipeline validation is unchanged.</span></div>
      </div></div>`;

  html += `
    ${flowStrip}
    <div style="margin-top:8px">${collector}</div>
    <div class="gp-dash-panel" style="margin-top:8px"><h3>Source Registry</h3><div id="srcRegistry"></div></div>
    ${manifestBlock}
    ${validationBlock}
    ${historyBlock}
    ${govBlock}
    ${errorList.length ? `
      <div class="gp-dash-panel" style="margin-top:8px"><h3>Recent fetch errors</h3>
        ${errorList.map(([k, v]) => `<div style="font-size:12px"><strong>${esc(k)}</strong>: ${esc(v)}</div>`).join('')}</div>` : ''}
    <div style="margin-top:10px;font-size:11px;color:var(--muted-2)">
      Aegis Nexus uses only public open sources. Source availability can change. Always verify critical claims against primary sources.
    </div>
  `;
  el.innerHTML = html;

  el.querySelectorAll('[data-status-filter]').forEach(btn => btn.addEventListener('click', () => {
    statusFilter = btn.dataset.statusFilter; showAllSources = false; renderStatus();
  }));
  el.querySelector('#statusSearch')?.addEventListener('input', event => {
    statusQuery = String(event.target.value || '').trim().toLowerCase(); showAllSources = false; renderStatus();
    const input = document.getElementById('statusSearch'); input?.focus(); input?.setSelectionRange(input.value.length, input.value.length);
  });
  el.querySelector('#statusMore')?.addEventListener('click', () => { showAllSources = !showAllSources; renderStatus(); });
  el.querySelector('#govSave')?.addEventListener('click', () => {
    const clamp = (value, lo, hi, fallback) => {
      const n = Number(value);
      return Number.isFinite(n) ? Math.min(hi, Math.max(lo, Math.round(n))) : fallback;
    };
    saveGov({
      sourceFailure: clamp(document.getElementById('govSource')?.value, 1, 24, 3),
      validationFailure: clamp(document.getElementById('govValidation')?.value, 1, 24, 5),
      freshnessMinutes: clamp(document.getElementById('govFresh')?.value, 5, 1440, 60)
    });
    renderStatus();
  });

  renderRegistry(Array.isArray(sourceHealth?.sources) ? sourceHealth.sources : []);
}
