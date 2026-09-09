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

function stateBadge(kind, label) {
  return `<span class="gp-sev gp-sev-${kind}">${esc(label)}</span>`;
}

function registryRows(list) {
  return list.map(s => {
    const kind = sourceState(s);
    const label = kind === 'healthy' ? 'Online' : kind === 'critical' ? 'Failing' : 'Degraded';
    const fails = s.consecutiveFailures === undefined || s.consecutiveFailures === null ? '' : `<div class="meta">${fmtInt(s.consecutiveFailures)} consecutive failures</div>`;
    const cred = credibilityTier(s);
    return `<div class="gp-dash-row"><div class="grow"><div class="title">${esc(s.name || s.url || 'Unnamed source')}</div>`
      + `<div class="meta">${esc(s.category || s.type || 'uncategorized')} · ${fmtInt(s.rowsFetched)} rows · checked ${esc(formatRelativeTime(s.lastChecked))} · <span title="Derived: no failures + fresh rows = High; ≤2 failures + rows = Medium; else Low">credibility ${cred}</span> · fallback ${esc(fallbackMode(s))}</div>${fails}</div>`
      + `<div>${stateBadge(kind, label)}</div></div>`;
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
    + (shown.length ? `<div class="gp-dash-list gp-source-table-dense">${registryRows(shown)}</div><div class="meta gp-nums" style="margin-top:6px;font-size:10px;color:var(--muted-2)">Showing ${shown.length} of ${ordered.length} matching sources</div>` : '<div class="gp-state"><div class="gp-state-title">No sources match</div><div>No registry entries match the current filter.</div></div>')
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
    el.innerHTML = '<div class="gp-state" role="status" aria-live="polite"><div class="gp-spinner" aria-hidden="true"></div><div>Loading source health…</div></div>';
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
    const kpiStrip = `<div class="cc-kpi-strip gp-source-kpis" role="list" aria-label="Source indicators">`
      + `<div class="cc-kpi t-blue"><div class="v gp-nums">${total}</div><div class="l">Active Sources</div></div>`
      + `<div class="cc-kpi t-green"><div class="v gp-nums">${onlineWithData}</div><div class="l">Reporting with Data</div></div>`
      + `<div class="cc-kpi t-red"><div class="v gp-nums">${failedCount}</div><div class="l">Sources with Issues</div></div>`
      + `<div class="cc-kpi t-amber"><div class="v gp-nums">${Number.isFinite(coverage) ? coverage.toFixed(0) + '%' : '—'}</div><div class="l">Data Coverage</div></div></div>`;

    html += kpiStrip + `
    <div class="gp-card gp-source-summary sev-${pillSev}">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
        <div>
          <div class="gp-micro-label" style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">Overall Status</div>
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
      + `<span class="meta gp-nums gp-micro-label" style="align-self:center;font-size:10px;color:var(--muted-2)">Showing ${shown.length} of ${visible.length} sources</span></div>`
      + (rows ? `<div class="gp-source-table-dense gp-dash-list" role="list" aria-label="Source health">${rows}</div>` : '<div class="gp-state"><div class="gp-state-title">No sources match</div><div>Nothing in the health registry matches this state or search.</div></div>')
      + (visible.length > SOURCE_PAGE ? `<button id="statusMore" class="gp-btn gp-more" type="button">${showAllSources ? 'Show fewer' : `Show all ${visible.length}`}</button>` : '');

    if (stamp) stamp.textContent = sourceHealth.updatedAt ? `Updated ${formatRelativeTime(sourceHealth.updatedAt)} · ${online.length}/${list.length} online` : '';
  }

  const live = liveStatus || {};
  const failedSources = Array.isArray(live.failedSources) ? live.failedSources : [];
  const manifest = refreshManifest || {};
  const artifacts = manifest.artifacts && typeof manifest.artifacts === 'object' ? Object.entries(manifest.artifacts) : [];
  const errorList = Object.entries(errors || {});

  const collector = live && live.updatedAt ? `
      <div class="gp-dash-grid" role="list" aria-label="Collector telemetry">
        <div class="gp-dash-panel" role="listitem"><h3>Latest Collector Run</h3>
          <div class="gp-kpi-value gp-nums" style="font-size:20px">${esc(formatRelativeTime(live.updatedAt))}</div>
          <div class="meta" style="font-size:10px;color:var(--muted-2)">${fmtInt(live.feedsChecked)} feeds checked · ${fmtInt(live.rowsFetched)} rows · ${fmtInt(live.newArticles)} new · ${fmtInt(live.exportedArticles)} exported</div></div>
        <div class="gp-dash-panel" role="listitem"><h3>Collector Health</h3>
          <div class="gp-kpi-value gp-nums" style="font-size:20px;color:var(--sev-healthy)">${fmtInt(live.healthySources)}</div>
          <div class="meta" style="font-size:10px;color:var(--muted-2)">healthy · ${fmtInt(live.emptySources)} empty · ${fmtInt(failedSources.length)} failed</div></div>
      </div>
      ${failedSources.length ? `<div class="gp-dash-panel" style="margin-top:8px"><h3>Recent Collector Issues (${failedSources.length > 5 ? `showing 5 of ${failedSources.length}` : failedSources.length})</h3><div class="gp-dash-list gp-source-table-dense">`
        + failedSources.slice(0, 5).map(f => `<div class="gp-dash-row"><div class="grow"><div class="title">${esc(f.source || 'Unnamed feed')}</div><div class="meta">${esc(String(f.error || 'unknown error').slice(0, 160))}</div></div></div>`).join('')
        + '</div></div>' : '<div class="gp-dash-panel" style="margin-top:8px"><h3>Recent Collector Issues</h3><div class="meta">No collector failures recorded in this run.</div></div>'}` : `
      <div class="gp-dash-panel" role="status" aria-live="polite"><h3>Latest Collector Run</h3>
        <div class="gp-state" style="padding:12px"><div class="gp-state-title">No collector run recorded yet</div><div>Collector telemetry publishes on the next pipeline refresh.</div></div></div>`;

  const manifestBlock = artifacts.length ? `
      <div class="gp-dash-panel" style="margin-top:8px"><h3>Artifact Integrity</h3>
        <div class="meta gp-micro-label" style="font-size:10px;color:var(--muted-2);margin-bottom:6px">Manifest-recorded hashes · generated ${esc(formatRelativeTime(manifest.generatedAt))}</div>
        <div class="gp-dash-list gp-source-table-dense" role="table" aria-label="Artifact integrity">` + artifacts.map(([name, meta]) => `
          <div class="gp-dash-row" role="row"><div class="grow"><div class="title" style="font-family:var(--font-mono);font-size:11px">${esc(name)}</div>
          <div class="meta">sha256 ${esc(String(meta.sha256 || '').slice(0, 12))}… · ${esc(fmtSize(meta.size))}</div></div></div>`).join('')
      + '</div></div>' : `
      <div class="gp-dash-panel" style="margin-top:8px" role="status" aria-live="polite"><h3>Artifact Integrity</h3>
        <div class="gp-state" style="padding:12px"><div class="gp-state-title">No manifest recorded yet</div><div>Artifact hashes publish on the next pipeline refresh.</div></div></div>`;

  const vSummary = validationResults?.summary || {};
  const vResults = Array.isArray(validationResults?.results) ? validationResults.results : [];
  const vRan = Number(vSummary.run ?? vResults.length);
  const vPassed = Number(vSummary.passed ?? vResults.filter(r => r.passed).length);
  const vFailed = Number(vSummary.failed ?? vResults.filter(r => !r.passed).length);
  const validationBlock = `
      <div class="gp-dash-panel" style="margin-top:8px"><h3>Validation &amp; Data Contracts</h3>
        ${vResults.length ? `<div class="meta gp-nums" style="font-size:10px;color:var(--muted-2);margin-bottom:6px">${fmtInt(vRan)} run · ${fmtInt(vPassed)} passed · ${fmtInt(vFailed)} failed · recorded ${esc(formatRelativeTime(validationResults.updatedAt))}</div>
        <div class="gp-dash-list gp-source-table-dense">` + vResults.map(r => `
          <div class="gp-dash-row"><div class="grow"><div class="title" style="font-size:11px">${esc(r.contract || r.command || 'contract')}</div>
          <div class="meta">${esc(String(r.detail || '').slice(0, 160))}</div></div>
          <div>${r.passed ? '<span class="gp-sev gp-sev-healthy">Passed</span>' : '<span class="gp-sev gp-sev-critical">Failed</span>'}</div></div>`).join('')
        + '</div>' : '<div class="meta">No validation run recorded yet — published by the next pipeline refresh.</div>'}</div>`;

  const runs = Array.isArray(pipelineHistory?.runs) ? pipelineHistory.runs : [];
  const historyBlock = `
      <div class="gp-dash-panel" style="margin-top:8px"><h3>Pipeline Run History</h3>
        ${runs.length ? `<div class="gp-dash-list gp-source-table-dense">` + runs.slice(0, 8).map(r => {
          const ok = String(r.status || '').toLowerCase() === 'success';
          const dur = Number.isFinite(Number(r.durationSeconds)) ? `${Number(r.durationSeconds).toFixed(0)}s` : '—';
          return `<div class="gp-dash-row"><div class="grow"><div class="title" style="font-family:var(--font-mono);font-size:11px">${esc(String(r.runId || 'run').slice(0, 24))}</div>
          <div class="meta">${esc(r.trigger || 'manual')} · ${esc(formatRelativeTime(r.startedAt))} · ${esc(dur)}${r.error ? ` · ${esc(String(r.error).slice(0, 120))}` : ''}</div></div>
          <div>${ok ? '<span class="gp-sev gp-sev-healthy">Success</span>' : '<span class="gp-sev gp-sev-critical">Failed</span>'}</div></div>`;
        }).join('') + '</div>' : '<div class="meta">No run history yet — recorded on the next pipeline refresh.</div>'}</div>`;

  const snapStories = Array.isArray(snapshot?.stories) ? snapshot.stories.length : 0;
  const snapConflicts = Array.isArray(snapshot?.conflicts) ? snapshot.conflicts.length : 0;
  const brainNodes = Array.isArray(intelligenceBrain?.nodes) ? intelligenceBrain.nodes.length : 0;
  const brainEdges = Array.isArray(intelligenceBrain?.edges) ? intelligenceBrain.edges.length : 0;
  const stage = (label, value, sub, kind) => `<div class="gp-dash-panel" style="flex:1;min-width:120px"><h3>${label}</h3><div class="gp-kpi-value" style="font-size:18px;color:${kind === 'healthy' ? 'var(--sev-healthy)' : kind === 'watch' ? 'var(--sev-watch)' : kind === 'critical' ? 'var(--sev-critical)' : 'var(--text)'}">${value}</div><div class="meta" style="font-size:10px;color:var(--muted-2)">${sub}</div></div>`;
  const flowStrip = `
      <div class="gp-dash-panel" style="margin-top:8px"><h3>Refresh Pipeline Health</h3>
      <div style="display:flex;gap:6px;flex-wrap:wrap">`
      + stage('Ingest', live?.updatedAt ? `${fmtInt(live.feedsChecked)} feeds` : '—', live?.updatedAt ? `${fmtInt(live.rowsFetched)} rows · ${esc(formatRelativeTime(live.updatedAt))}` : 'no collector run', live?.updatedAt && Number(live.rowsFetched) > 0 ? 'healthy' : 'info')
      + stage('Validate', vResults.length ? `${fmtInt(vPassed)}/${fmtInt(vRan)}` : '—', vResults.length ? `gates passed${vFailed ? ` · ${fmtInt(vFailed)} failing` : ''}` : 'no validation run', !vResults.length ? 'info' : vFailed ? 'critical' : 'healthy')
      + stage('Transform', snapStories ? fmtInt(snapStories) : '—', snapStories ? `${fmtInt(snapConflicts)} conflicts normalized` : 'no snapshot', snapStories ? 'healthy' : 'info')
      + stage('Enrich', brainNodes ? fmtInt(brainNodes) : '—', brainNodes ? `${fmtInt(brainEdges)} brain edges` : 'no brain', brainNodes ? 'healthy' : 'info')
      + stage('Publish', artifacts.length ? fmtInt(artifacts.length) : '—', artifacts.length ? `artifacts · ${esc(formatRelativeTime(manifest.generatedAt))}` : 'no manifest', artifacts.length ? 'healthy' : 'info')
      + `</div></div>`;

  html += `
    ${flowStrip}
    <div style="margin-top:8px">${collector}</div>
    <div class="gp-dash-panel" style="margin-top:8px"><h3>Source Registry</h3><div id="srcRegistry"></div></div>
    ${manifestBlock}
    ${validationBlock}
    ${historyBlock}
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

  renderRegistry(Array.isArray(sourceHealth?.sources) ? sourceHealth.sources : []);
}
