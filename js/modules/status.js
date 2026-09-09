/** GUI Phase 6 — Sources / Validation / System Health workspace.
 * Every figure is read from the canonical source-health artifact
 * (data/source_health.json with summary/sources) plus fetch errors.
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

function sourceDetail(source) {
  const parts = [];
  if (source?.type || source?.category) parts.push(String(source.type || source.category));
  if (source?.contentStatus) parts.push(String(source.contentStatus).replace(/_/g, ' '));
  if (Number.isFinite(Number(source?.freshnessMinutes))) parts.push(`${Number(source.freshnessMinutes).toFixed(0)}m fresh`);
  const fails = Number(source?.consecutiveFailures || 0);
  if (fails > 0) parts.push(`${fails} consecutive failure${fails === 1 ? '' : 's'}`);
  return parts.join(' · ');
}
export function renderStatus() {
  const el = document.getElementById('statusBody');
  if (!el) return;

  const { status, lastSuccessfulFetch, sourceHealth, errors } = getState();
  const stamp = document.getElementById('statusUpdated');

  if (!sourceHealth && status === 'loading') {
    el.innerHTML = '<div class="gp-state"><div class="gp-spinner"></div><div>Loading source health…</div></div>';
    return;
  }
  if (!sourceHealth) {
    el.innerHTML = '<div class="gp-state"><div class="gp-state-title">Source health unavailable</div><div>Health telemetry failed to load. Check fetch errors below.</div></div>';
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
    const kpiStrip = `<div class="cc-kpi-strip" role="list" aria-label="Source indicators" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:10px">`
      + `<div class="cc-kpi t-blue"><div class="v">${total}</div><div class="l">Active Sources</div></div>`
      + `<div class="cc-kpi t-green"><div class="v">${onlineWithData}</div><div class="l">Reporting with Data</div></div>`
      + `<div class="cc-kpi t-red"><div class="v">${failedCount}</div><div class="l">Sources with Issues</div></div>`
      + `<div class="cc-kpi t-amber"><div class="v">${Number.isFinite(coverage) ? coverage.toFixed(0) + '%' : '—'}</div><div class="l">Data Coverage</div></div></div>`;

    el.innerHTML = kpiStrip + `
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

    el.querySelectorAll('[data-status-filter]').forEach(btn => btn.addEventListener('click', () => {
      statusFilter = btn.dataset.statusFilter; showAllSources = false; renderStatus();
    }));
    el.querySelector('#statusSearch')?.addEventListener('input', event => {
      statusQuery = String(event.target.value || '').trim().toLowerCase(); showAllSources = false; renderStatus();
      const input = document.getElementById('statusSearch'); input?.focus(); input?.setSelectionRange(input.value.length, input.value.length);
    });
    el.querySelector('#statusMore')?.addEventListener('click', () => { showAllSources = !showAllSources; renderStatus(); });

    if (stamp) stamp.textContent = sourceHealth.updatedAt ? `Updated ${formatRelativeTime(sourceHealth.updatedAt)} · ${online.length}/${list.length} online` : '';
  }

  const errorList = Object.entries(errors || {});
  if (errorList.length) {
    el.insertAdjacentHTML('beforeend',
      `<div class="gp-card" style="margin-top:10px;border-color:var(--red-dim)"><div style="font-weight:700;color:var(--red);margin-bottom:6px">Recent errors</div>${errorList.map(([k, v]) => `<div style="font-size:12px"><strong>${escapeHtml(k)}</strong>: ${escapeHtml(v)}</div>`).join('')}</div>`);
  }
  el.insertAdjacentHTML('beforeend',
    '<div style="margin-top:14px;font-size:11px;color:var(--muted-2)">Global Pulse uses only public open sources. Source availability can change. Always verify critical claims against primary sources.</div>');
}
