/** GUI Phase 1 — Command Center Dashboard.
 * Every figure below is read from canonical state (snapshot, live articles,
 * live events, regional intelligence, what-changed, market data, source
 * health). Nothing is fabricated: missing data renders an honest empty
 * state instead of a placeholder number. Severity follows the shared
 * language — blue informational, amber watch, red critical, green healthy. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

let query = '';

function fmtInt(value) {
  return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : '—';
}

function fmtPrice(value) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    : '—';
}

function itemTime(item) {
  return item.published || item.publishedAt || item.published_date || item.publishedDate
    || item.time || item.date || item.lastSeen || item.firstSeen || item.updatedAt || null;
}

function storyItems(state) {
  const { liveArticles, snapshot } = state;
  const raw = Array.isArray(liveArticles) ? liveArticles
    : liveArticles?.articles || snapshot?.stories || snapshot?.liveArticles || [];
  return [...raw].sort((a, b) => new Date(itemTime(b) || 0) - new Date(itemTime(a) || 0));
}

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

function tensionSeverity(level) {
  const text = String(level || '');
  if (/crit/i.test(text)) return 'critical';
  if (/high|elev|watch/i.test(text)) return 'watch';
  return 'info';
}

function kpi(value, label, sub, sev) {
  return `<div class="gp-kpi sev-${sev}"><div class="gp-kpi-value">${value}</div>`
    + `<div class="gp-kpi-label">${esc(label)}</div>`
    + (sub ? `<div class="gp-kpi-sub">${esc(sub)}</div>` : '') + `</div>`;
}

function renderHeadlines(items) {
  const box = document.getElementById('dashHeadlines');
  if (!box) return;
  const q = query.trim().toLowerCase();
  const filtered = q
    ? items.filter(item => `${item.title || item.headline || ''} ${item.summary || item.summary_snippet || ''} ${item.sourceLabel || item.sourceName || item.source || ''}`.toLowerCase().includes(q))
    : items;
  if (!filtered.length) {
    box.innerHTML = q
      ? '<div class="gp-state"><div class="gp-state-title">No matching reports</div><div>No headlines match the current search.</div></div>'
      : '<div class="gp-state"><div class="gp-state-title">No recent reports</div><div>Live article feed is empty or unavailable. Check source health below.</div></div>';
    return;
  }
  box.innerHTML = '<div class="gp-dash-list">' + filtered.slice(0, 6).map(item => {
    const title = item.title || item.headline || 'Untitled';
    const summary = item.summary || item.summary_snippet || item.description || '';
    const source = item.sourceLabel || item.sourceName || item.source || 'Unknown source';
    const url = item.url || item.link || '#';
    return `<div class="gp-dash-row"><div class="grow"><div class="title"><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(title)}</a></div>`
      + (summary ? `<div class="meta">${esc(String(summary).slice(0, 140))}</div>` : '')
      + `<div class="meta">${esc(source)} · ${esc(formatRelativeTime(itemTime(item)))}</div></div></div>`;
  }).join('') + '</div>';
}

function renderStatusPill(state) {
  const pill = document.getElementById('commandStatus');
  if (!pill) return;
  const health = state.sourceHealth;
  const summary = health?.summary || {};
  const total = Number(summary.total ?? (Array.isArray(health?.sources) ? health.sources.length : 0));
  const failed = Number(summary.failed ?? 0);
  const updated = health?.updatedAt || state.snapshot?.updatedAt;
  if (!health || !total) {
    pill.className = 'gp-status-pill';
    pill.innerHTML = '<span class="dot"></span><span>Status unknown</span>';
    return;
  }
  const sev = failed === 0 ? 'healthy' : 'watch';
  pill.className = `gp-status-pill sev-${sev}`;
  pill.innerHTML = `<span class="dot"></span><span>${failed === 0 ? 'All Systems Operational' : `${failed} source${failed === 1 ? '' : 's'} failing`}</span>`
    + (updated ? `<span>· ${esc(formatRelativeTime(updated))}</span>` : '');
}

export function renderDashboard() {
  const el = document.getElementById('dashboardBody');
  if (!el) return;
  const state = getState();
  const { snapshot, sourceHealth, mapData, whatChanged, status } = state;

  if (!snapshot && !state.liveArticles && !mapData) {
    el.innerHTML = status === 'loading'
      ? '<div class="gp-state"><div class="gp-spinner"></div><div>Loading command overview…</div></div>'
      : '<div class="gp-state"><div class="gp-state-title">Command overview unavailable</div><div>Core data failed to load. Check source health below.</div></div>';
    renderStatusPill(state);
    return;
  }

  const events = Array.isArray(mapData?.events?.events) ? mapData.events.events : [];
  const regional = mapData?.regional || {};
  const regions = regional.regions || {};
  const order = Array.isArray(regional.priorityOrder) ? regional.priorityOrder : Object.keys(regions);
  const wc = whatChanged || {};
  const wcItems = Array.isArray(wc.items) ? wc.items : [];
  const health = sourceHealth || {};
  const summary = health.summary || {};
  const total = Number(summary.total ?? (Array.isArray(health.sources) ? health.sources.length : 0));
  const online = Number(summary.onlineWithData ?? summary.online ?? 0);
  const failed = Number(summary.failed ?? 0);
  const market = snapshot?.marketData || {};
  const indicators = Array.isArray(market.indicators) ? market.indicators.filter(x => x && typeof x === 'object') : [];
  const conflicts = Array.isArray(snapshot?.conflicts) ? snapshot.conflicts : [];
  const tension = snapshot?.tension;
  const tensionLevel = snapshot?.earlyWarning?.level || '';
  const stories = storyItems(state);

  const cards = [
    kpi(fmtInt(events.length), 'Active Events', events.length && mapData?.events?.updatedAt ? `updated ${formatRelativeTime(mapData.events.updatedAt)}` : 'tracked clusters', 'info'),
    kpi(fmtInt(conflicts.length), 'Conflict Watch', 'active conflicts', conflicts.length ? 'watch' : 'info'),
    kpi(tension === undefined || tension === null ? '—' : fmtInt(tension), 'Global Tension', `${tensionLevel || 'ungraded'}${snapshot?.tensionDelta === undefined ? '' : ` · Δ ${snapshot.tensionDelta}`}`, tensionSeverity(tensionLevel)),
    kpi(fmtInt(order.length), 'Monitored Regions', 'regions', 'info'),
    kpi(total ? `${fmtInt(online)}/${fmtInt(total)}` : '—', 'Sources Reporting', total ? `${fmtInt(failed)} failed` : 'no health data', total ? (failed === 0 ? 'healthy' : 'watch') : 'info'),
  ].join('');

  const regionRows = order.slice(0, 6).map(name => {
    const r = regions[name] || {};
    const trend = String(r.trend || '').toUpperCase();
    const arrow = trend === 'UP' ? '<span class="gp-trend-up">▲</span>' : trend === 'DOWN' ? '<span class="gp-trend-down">▼</span>' : '<span class="gp-trend-flat">—</span>';
    return `<div class="gp-region-bar"><span class="rname">${esc(name)}</span>`
      + `<span class="meta">${fmtInt(r.reports)} reports · ${fmtInt(r.conflictReports)} conflict</span>${arrow}</div>`;
  }).join('') || '<div class="gp-state"><div class="gp-state-title">No regional data</div><div>Regional intelligence has not been generated.</div></div>';

  const wcRows = wcItems.slice(0, 5).map(item => {
    const title = item.title || item.eventId || 'Change';
    const detail = item.detail || item.summary || '';
    return `<div class="gp-dash-row"><div class="grow"><div class="title">${esc(title)}</div>`
      + (detail ? `<div class="meta">${esc(String(detail).slice(0, 140))}</div>` : '') + '</div></div>';
  }).join('');
  const wcSummary = wc.summary || {};
  const wcBlock = wcItems.length
    ? `<div class="gp-dash-list">${wcRows}</div><div class="meta" style="margin-top:6px;font-size:10px;color:var(--muted-2)">${fmtInt(wcSummary.newEvents)} new events · ${fmtInt(wcSummary.indicatorMoves)} indicator moves</div>`
    : '<div class="gp-state"><div class="gp-state-title">Nothing new this window</div><div>No changes recorded in the current window.</div></div>';

  const marketRows = indicators.slice(0, 6).map(item => {
    const name = item.name || item.symbol || 'Indicator';
    const pct = Number(item.changePercent);
    const cls = Number.isFinite(pct) ? (pct >= 0 ? 'gp-up' : 'gp-down') : '';
    const arrow = Number.isFinite(pct) ? (pct >= 0 ? '▲' : '▼') : '';
    const pctText = Number.isFinite(pct) ? `${arrow} ${Math.abs(pct).toFixed(2)}%` : '—';
    return `<div class="gp-market-row"><span class="mname">${esc(name)}</span>`
      + `<span class="mprice">${esc(fmtPrice(item.price))}</span><span class="${cls}">${esc(pctText)}</span></div>`;
  }).join('') || '<div class="gp-state"><div class="gp-state-title">Market data unavailable</div><div>Public delayed market feed is not present.</div></div>';

  const issues = Array.isArray(health.sources) ? health.sources.filter(s => s && s.status && s.status !== 'online') : [];
  const issueRows = issues.slice(0, 4).map(s => {
    const fails = s.consecutiveFailures === undefined || s.consecutiveFailures === null ? '' : ` · ${s.consecutiveFailures} consecutive failures`;
    return `<div class="gp-health-issue"><div class="grow"><div class="title">${esc(s.name || 'Unnamed source')}</div>`
      + `<div class="meta">${esc(s.status || 'unknown')}${esc(fails)}${s.lastChecked ? ` · ${esc(formatRelativeTime(s.lastChecked))}` : ''}</div></div></div>`;
  }).join('');
  const healthBlock = total
    ? (issues.length ? `<div>${issueRows}</div>` : '<div class="gp-state"><div class="gp-state-title">All reporting sources online</div></div>')
    : '<div class="gp-state"><div class="gp-state-title">Source health unavailable</div><div>Health telemetry has not been generated.</div></div>';

  const search = document.getElementById('dashSearch');
  if (search && document.activeElement !== search) search.value = query;
  const q = search ? search.value : query;
  query = q || '';

  el.innerHTML = `
    <div class="gp-kpi-grid">${cards}</div>
    <div class="gp-dash-grid">
      <div class="gp-dash-panel"><h3>Headline Intelligence <a href="#section-breaking">View All →</a></h3>
        <input id="dashSearch" class="gp-dash-search" type="search" aria-label="Filter headlines" placeholder="Filter headlines…" value="${esc(query)}">
        <div id="dashHeadlines"></div></div>
      <div class="gp-dash-panel"><h3>Priority Regions <a href="#section-map">View Map →</a></h3>
        <div class="gp-dash-list">${regionRows}</div></div>
      <div class="gp-dash-panel"><h3>What Changed <a href="#section-breaking">View Reporting →</a></h3>${wcBlock}</div>
      <div class="gp-dash-panel"><h3>Market Pulse <span class="gp-badge delayed">DELAYED</span> <a href="#section-markets">View Markets →</a></h3>
        <div class="meta" style="font-size:10px;color:var(--muted-2);margin-bottom:4px">${esc(market.provider || market.source || 'Public delayed feed')}${market.updatedAt ? ` · ${esc(formatRelativeTime(market.updatedAt))}` : ''}</div>
        <div>${marketRows}</div></div>
      <div class="gp-dash-panel"><h3>Source Health <a href="#section-status">View Sources →</a></h3>${healthBlock}</div>
    </div>`;

  renderHeadlines(stories);
  const input = document.getElementById('dashSearch');
  input?.addEventListener('input', () => { query = input.value; renderHeadlines(storyItems(getState())); });
  renderStatusPill(state);
  const stamp = document.getElementById('dashboardUpdated');
  if (stamp) stamp.textContent = state.snapshot?.updatedAt ? `Updated ${formatRelativeTime(state.snapshot.updatedAt)}` : '';
}
