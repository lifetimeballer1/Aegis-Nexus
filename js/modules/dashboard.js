/** Command Center Dashboard — Concept 01 fidelity.
 * All figures from canonical state only. No fabrication. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';
import { sparklineSVG } from '../core/sparkline.js';

let query = '';
const regionSort = { key: 'activity', dir: -1 };
function trendRank(t) {
  const s = String(t || '').toUpperCase();
  if (s === 'UP') return 2;
  if (s === 'DOWN') return 0;
  return 1;
}

function fmtInt(v) { return Number.isFinite(Number(v)) ? Number(v).toLocaleString() : '—'; }
function esc(v) { return escapeHtml(String(v ?? '')); }
function itemTime(i) { return i.published || i.publishedAt || i.published_date || i.publishedDate || i.time || i.date || i.lastSeen || i.firstSeen || i.updatedAt || null; }
function stories(state) {
  const { liveArticles, snapshot } = state;
  const raw = Array.isArray(liveArticles) ? liveArticles : liveArticles?.articles || snapshot?.stories || [];
  return [...raw].sort((a, b) => new Date(itemTime(b) || 0) - new Date(itemTime(a) || 0));
}
function catPill(cat, title = '') {
  const c = `${cat || ''} ${title || ''}`.toLowerCase();
  if (/cyber|ransom|malware|hack|sigint/.test(c)) return ['cyber', 'CYBER'];
  if (/econ|market|oil|brent|gold|trade|stimulus|financial/.test(c)) return ['econ', 'ECONOMIC'];
  if (/climate|hazard|gdacs|earthquake|flood|wildfire|storm|usgs/.test(c)) return ['geo', 'CLIMATE'];
  if (/indo|pacific|asia|china|taiwan/.test(c)) return ['indo', 'INDO-PACIFIC'];
  if (/us-politics|domestic|america|crime|city|cartel|enforcer/.test(c)) return ['dom', 'DOMESTIC'];
  if (/geopol|conflict|war|diplo|middle|europe|israel|ukraine|iran|russia|gaza|lebanon/.test(c)) return ['geo', 'GEOPOLITICAL'];
  return ['gen', String(cat || 'GENERAL').slice(0, 12).toUpperCase()];
}
function blocks(n, max) {
  const ratio = max > 0 ? (Number(n) || 0) / max : 0;
  const f = Math.round(ratio * 5);
  const cls = ratio >= 0.66 ? 'f-r' : ratio >= 0.33 ? 'f-a' : 'f-b';
  let s = '';
  for (let i = 0; i < 5; i++) s += `<i class="${i < f ? cls : ''}"></i>`;
  return `<span class="cc-blocks" aria-hidden="true">${s}</span>`;
}
function trendArrow(t) {
  const s = String(t || '').toUpperCase();
  if (s === 'UP') return '<span style="color:var(--red);font-weight:800">↑</span>';
  if (s === 'DOWN') return '<span style="color:var(--green);font-weight:800">↓</span>';
  return '<span style="color:var(--muted)">—</span>';
}
// Shared severity language (locked by GUI Phase 1 contract): blue info, amber watch, red critical, green healthy.
function sevFor(kind) {
  if (kind === 'critical') return 'critical';
  if (kind === 'watch') return 'watch';
  if (kind === 'healthy') return 'healthy';
  return 'info';
}
const SEV_LEVELS = ['info', 'watch', 'critical', 'healthy'];
function kpi(value, label, sub, tone, sparkVals, sparkColor) {
  return `<div class="cc-kpi t-${tone}"><div class="v">${value}</div><div class="l">${esc(label)}${sub ? ` <span style="font-weight:400;color:var(--muted-2)">· ${esc(sub)}</span>` : ''}</div>${sparklineSVG(sparkVals, { stroke: sparkColor })}</div>`;
}
function donut(healthy, degraded, failed, unknown) {
  const t = (Number(healthy) || 0) + (Number(degraded) || 0) + (Number(failed) || 0) + (Number(unknown) || 0);
  const c = 2 * Math.PI * 30;
  if (!(t > 0)) return `<svg width="96" height="96" viewBox="0 0 96 96" role="img" aria-label="Source health unavailable"><circle cx="48" cy="48" r="30" fill="none" stroke="var(--line-strong)" stroke-width="10"/><text x="48" y="52" text-anchor="middle" fill="var(--muted)" font-size="12">—</text></svg>`;
  const segs = [[healthy, 'var(--green)'], [degraded, 'var(--amber)'], [failed, 'var(--red)'], [unknown, 'var(--muted-2)']];
  let acc = 0;
  const arcs = segs.map(([n, color]) => {
    const frac = (Number(n) || 0) / t;
    const len = frac * c;
    const s = `<circle cx="48" cy="48" r="30" fill="none" stroke="${color}" stroke-width="10" stroke-dasharray="${len.toFixed(1)} ${(c - len).toFixed(1)}" stroke-dashoffset="${(-acc * c).toFixed(1)}" transform="rotate(-90 48 48)"/>`;
    acc += frac;
    return frac > 0 ? s : '';
  }).join('');
  const pct = (Number(healthy) || 0) / t * 100;
  return `<svg width="96" height="96" viewBox="0 0 96 96" role="img" aria-label="Source health ${pct.toFixed(0)} percent with data"><circle cx="48" cy="48" r="30" fill="none" stroke="var(--line-strong)" stroke-width="10"/>${arcs}<text x="48" y="46" text-anchor="middle" fill="var(--text)" font-size="16" font-weight="800">${pct.toFixed(0)}%</text><text x="48" y="60" text-anchor="middle" fill="var(--muted)" font-size="9">With data</text></svg>`;
}

export function renderDashboard() {
  const el = document.getElementById('dashboardBody');
  if (!el) return;
  const state = getState();
  const { snapshot, sourceHealth, mapData, whatChanged, status, feedMeta, historicalTrends, brainStories } = state;
  if (!snapshot && !state.liveArticles && !mapData) {
    el.innerHTML = status === 'loading'
      ? '<div class="gp-state"><div class="gp-spinner"></div><div>Loading command overview…</div></div>'
      : '<div class="gp-state"><div class="gp-state-title">Command overview unavailable</div><div>Core data failed to load.</div></div>';
    return;
  }
  const events = Array.isArray(mapData?.events?.events) ? mapData.events.events : [];
  const conflicts = Array.isArray(snapshot?.conflicts) ? snapshot.conflicts : [];
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
  const tension = snapshot?.tension;
  const tensionDelta = snapshot?.tensionDelta;
  const tSeries = Array.isArray(historicalTrends?.series) ? historicalTrends.series.map(s => s.tension).filter(Number.isFinite) : [];
  const lastT = tSeries.slice(-12);
  const tDelta = snapshot?.tensionDelta;
  const hiPri = conflicts.filter(c => /CRITICAL|HIGH/i.test(String(c.escalation || ''))).length;
  const critEv = events.filter(e => /high|confirmed/i.test(String(e.confidence || ''))).length;
  const emerging = events.filter(e => /low|limited|moderate/i.test(String(e.confidence || ''))).length;

  // KPI sparklines: tension series is real history; event spark uses real report counts; regions spark omitted (no history → honest, no spark).
  const evSpark = events.slice(0, 12).map(e => e.reportCount).filter(Number.isFinite);
  const kpis =
    kpi(fmtInt(events.length), 'Active Events', 'tracked clusters', 'blue', evSpark.length > 1 ? evSpark : lastT, '#62a0ff')
    + kpi(fmtInt(hiPri), 'High Priority', 'escalated conflicts', 'red', lastT, '#ff6678')
    + kpi(fmtInt(emerging), 'Emerging Risks', 'low-confidence events', 'amber', lastT, '#ffc857')
    + kpi(fmtInt(critEv), 'Critical Alerts', 'high-confidence events', 'red', lastT, '#ff6678')
    + kpi(fmtInt(order.length), 'Monitored Regions', 'regions', 'blue', [], '#62a0ff');

  const allStories = stories(state);
  const q = query.trim().toLowerCase();
  const filtered = q ? allStories.filter(s => `${s.title || s.headline || ''} ${s.summary || s.summary_snippet || ''} ${s.source || s.sourceName || ''}`.toLowerCase().includes(q)) : allStories;
  const headRows = filtered.slice(0, 5).map(s => {
    const [pc, pl] = catPill(s.category || s.sourceType, s.title);
    const title = s.title || s.headline || 'Untitled';
    const sum = (s.summary || s.summary_snippet || s.description || '').slice(0, 110);
    const initial = esc(String(title).trim().charAt(0).toUpperCase() || 'N');
    const url = s.url || s.link || '#';
    return `<div class="cc-head"><div class="cc-thumb" aria-hidden="true">${initial}</div><div style="min-width:0;flex:1"><div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap"><span class="cc-pill ${pc}">${esc(pl)}</span><span class="cc-time">${esc(formatRelativeTime(itemTime(s)))}</span></div><div class="t"><a href="${esc(url)}" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:none">${esc(title)}</a></div>${sum ? `<div class="s">${esc(sum)}</div>` : ''}</div></div>`;
  }).join('') || '<div class="gp-state"><div class="gp-state-title">No recent reports</div><div>Live article feed is empty.</div></div>';
  const wcEmptyNote = wcItems.length ? '' : '<!-- Nothing new this window — No changes recorded in the current window. -->';
  void sevFor;

  const maxRep = Math.max(1, ...order.map(n => Number(regions[n]?.reports) || 0));
  const maxConf = Math.max(1, ...order.map(n => Number(regions[n]?.conflictReports) || 0));
  const regionVal = (name, r) => {
    if (regionSort.key === 'region') return String(name).toLowerCase();
    if (regionSort.key === 'impact') return Number(r.conflictReports) || 0;
    if (regionSort.key === 'trend') return trendRank(r.trend);
    return Number(r.reports) || 0;
  };
  const sortedOrder = [...order].sort((a, b) => {
    const av = regionVal(a, regions[a] || {}), bv = regionVal(b, regions[b] || {});
    const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
    return cmp * regionSort.dir;
  });
  const sortArrow = (key) => regionSort.key === key ? (regionSort.dir < 0 ? ' ↓' : ' ↑') : '';
  const regionRows = sortedOrder.slice(0, 6).map((name, i) => {
    const r = regions[name] || {};
    return `<tr><td style="color:var(--muted)">${i + 1}</td><td>${esc(name)}</td><td>${blocks(r.reports, maxRep)}</td><td>${blocks(r.conflictReports, maxConf)}</td><td>${trendArrow(r.trend)}</td></tr>`;
  }).join('') || '<tr><td colspan="5" style="color:var(--muted)">No regional data</td></tr>';

  const wcSum = wc.summary || {};
  const wcBlock = `<div class="cc-wc"><b style="color:var(--green)">+ ${fmtInt(wcSum.newEvents ?? wcItems.length)}</b><span>New events added</span></div>`
    + (Number.isFinite(Number(wcSum.escalated)) ? `<div class="cc-wc"><b style="color:var(--red)">↑ ${fmtInt(wcSum.escalated)}</b><span>Events escalated in priority</span></div>` : '')
    + `<div class="cc-wc"><b style="color:var(--blue)">+ ${fmtInt(online)}</b><span>Sources reporting with data</span></div>`
    + `<div class="cc-wc"><b style="color:var(--red)">■ ${fmtInt(failed)}</b><span>Sources failed validation</span></div>`
    + `<div class="cc-wc"><b style="color:var(--amber)">▲ ${fmtInt(wcSum.indicatorMoves ?? 0)}</b><span>Significant indicator moves</span></div>`
    + (Number.isFinite(Number(wcSum.escalated)) ? '' : '<div class="gp-honest" style="margin-top:6px">Escalation and narrative-change categories are not published for this window; only the counters above are source-backed.</div>');

  const mktPref = ['S&P 500', 'Nasdaq Composite', 'Dow Jones', 'WTI Crude', 'Gold', 'EUR / USD', 'USD / JPY', 'VIX'];
  const byName = new Map(indicators.map(i => [String(i.name || i.symbol || ''), i]));
  const picked = mktPref.map(n => byName.get(n)).filter(Boolean);
  const mktList = picked.length >= 3 ? picked.slice(0, 8) : indicators.slice(0, 6);
  const mktOmitted = ['Brent', 'USD Index', 'DXY'].filter(n => !indicators.some(i => String(i.name || '').toLowerCase().includes(n.toLowerCase())));
  const bsStories = Array.isArray(brainStories?.stories)
    ? brainStories.stories.slice().sort((a, b) => (Number(b.tensionContribution) || 0) - (Number(a.tensionContribution) || 0)).slice(0, 3)
    : [];
  const bsOpenGaps = Number(brainStories?.stats?.open ?? (Array.isArray(brainStories?.gaps) ? brainStories.gaps.filter(g => g.state !== 'closed').length : 0));
  const storiesPanel = bsStories.length
    ? `<div class="cc-panel" style="margin-bottom:8px"><h3>🧠 What matters now <a href="#section-brain">View Brain →</a></h3><div class="gp-stack">${bsStories.map(s => `<div class="cc-wc" style="align-items:flex-start"><span class="gp-sev sev-${esc(s.severity || 'low')}">${esc(s.severity || 'low')}</span><span style="flex:1;min-width:0">${esc(String(s.title || '').slice(0, 110))}<span class="gp-tiny gp-muted" style="display:block">${esc(s.hub || 'site-wide')} · pressure ${esc(String(s.tensionContribution ?? 0))} · ${esc(String(s.confidence || 'unverified'))}</span></span></div>`).join('')}</div><div class="gp-tiny gp-muted" style="margin-top:4px">${bsOpenGaps} open evidence gaps tracked by the Brain; they close automatically as refreshes add source-backed evidence. Headlines live in <a href="#section-breaking">News</a>.</div></div>`
    : '';
  const mktCards = mktList.map(m => {
    const name = m.name || m.symbol || 'Indicator';
    const price = typeof m.price === 'number' ? m.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(m.price ?? m.last ?? '—');
    const pct = Number(m.changePercent ?? m.changePct);
    const up = Number.isFinite(pct) ? pct >= 0 : null;
    return `<div class="cc-mkt-card"><div class="n">${esc(String(name).slice(0, 18))}</div><div class="p">${esc(price)}</div><div class="c" style="color:${up == null ? 'var(--muted)' : up ? 'var(--green)' : 'var(--red)'}">${up == null ? '—' : `${up ? '↑' : '↓'} ${Math.abs(pct).toFixed(2)}%`}</div></div>`;
  }).join('') || '<div class="gp-state"><div class="gp-state-title">Market data unavailable</div></div>';

  const healthyCount = Number(summary.onlineWithData ?? online);
  const degradedCount = Math.max(0, Number(summary.onlineEmpty ?? (online - healthyCount)));
  const unknownCount = Math.max(0, total - online - failed);
  const allSources = Array.isArray(health.sources) ? health.sources : [];
  const issues = allSources.filter(s => String(s.status).toLowerCase() !== 'online').slice(0, 5);
  const issueRows = issues.length
    ? issues.map(s => `<div class="cc-wc" style="align-items:flex-start"><span class="gp-dot ${esc(String(s.status || 'unknown').toLowerCase())}" style="margin-top:4px"></span><span style="flex:1;min-width:0">${esc(s.name || 'Unnamed source')}<span class="gp-tiny gp-muted" style="display:block">${esc(s.status || 'unknown')}${Number(s.consecutiveFailures) > 0 ? ` · ${fmtInt(s.consecutiveFailures)} consecutive failures` : ''}${Number.isFinite(Number(s.freshnessMinutes)) ? ` · last success ${fmtInt(Math.round(Number(s.freshnessMinutes)))} min ago` : ''}</span></span></div>`).join('')
    : '<div class="gp-muted gp-tiny">No source issues in the current refresh.</div>';
  const marketData = snapshot?.marketData || market;
  void marketData; void tensionDelta; void SEV_LEVELS;
  const priorityOrder = Array.isArray(regional.priorityOrder) ? regional.priorityOrder : order;
  void priorityOrder;
  const stale = feedMeta && Object.values(feedMeta).some(f => f?.stale);
  const upd = snapshot?.updatedAt ? formatRelativeTime(snapshot.updatedAt) : '—';

  el.innerHTML = `
    <div class="cc-situation"><h2>🌐 Global Situation <span class="sub">Key indicators across all monitored domains</span></h2>
      <div class="meta"><span class="cc-pill ${tensionDelta > 0 ? 'geo' : tensionDelta < 0 ? 'econ' : 'gen'}" title="Global tension index">Tension ${tension ?? '—'}${Number.isFinite(Number(tensionDelta)) && Number(tensionDelta) !== 0 ? ` (${Number(tensionDelta) > 0 ? '+' : ''}${tensionDelta})` : ''}</span><span>⟳ Last updated: ${esc(upd)}</span><span class="cc-live sev-healthy"><i></i>${failed === 0 && total ? 'All Systems Operational' : `${failed} source${failed === 1 ? '' : 's'} failing`}</span></div></div>${wcEmptyNote}
    ${stale ? '<div class="gp-state" style="padding:8px;border:1px solid var(--amber-dim);border-radius:8px;margin-bottom:8px"><div style="font-size:11px;color:var(--amber)">Offline — showing cached data. Some feeds are stale.</div></div>' : ''}
    ${!navigator.onLine ? '<div class="gp-state" style="padding:8px;border:1px solid var(--red-dim);border-radius:8px;margin-bottom:8px"><div style="font-size:11px;color:var(--red)">You are offline. Cached snapshot shown.</div></div>' : ''}
    <div class="cc-kpi-strip" role="list" aria-label="Key indicators">${kpis}</div>
    ${storiesPanel}
    <div class="cc-grid">
      <div class="cc-panel"><h3>🌐 Global Map <a href="#section-map">View Full Map →</a></h3>
        <div style="font-size:11px;color:var(--muted);margin-bottom:6px">${fmtInt(Array.isArray(state.mapPoints?.markers) ? state.mapPoints.markers.length : 0)} mapped points · clustered bubbles · dark operational basemap</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">${order.slice(0, 6).map(n => `<span class="cc-pill gen">${esc(String(n).toUpperCase().slice(0, 14))} · ${fmtInt(regions[n]?.events ?? regions[n]?.reports)}</span>`).join('')}</div>
        <div id="dashMap" role="img" aria-label="Mini operational map" style="min-height:240px;height:260px;border:1px solid var(--line);border-radius:8px;background:#050b13;z-index:1"></div>
        <div class="cc-legend" aria-label="Map legend"><span><i style="background:var(--red)"></i>Critical</span><span><i style="background:var(--amber)"></i>Elevated</span><span><i style="background:var(--blue)"></i>Notable</span><span><i style="background:#cbd5e1"></i>Monitoring</span></div></div>
      <div class="cc-panel"><h3>🎯 Priority Regions <a href="#section-map">View All →</a></h3>
        <table class="cc-table" aria-label="Priority regions"><thead><tr><th>#</th><th><button type="button" class="gp-th-sort" data-sort="region">Region${sortArrow('region')}</button></th><th><button type="button" class="gp-th-sort" data-sort="activity">Activity${sortArrow('activity')}</button></th><th><button type="button" class="gp-th-sort" data-sort="impact">Impact${sortArrow('impact')}</button></th><th><button type="button" class="gp-th-sort" data-sort="trend">Trend${sortArrow('trend')}</button></th></tr></thead><tbody>${regionRows}</tbody></table>
        <h3 style="margin-top:10px">🕐 What Changed <a href="#section-breaking">View All →</a></h3><div style="font-size:10px;color:var(--muted-2);margin-bottom:6px">Since last refresh (${esc(wc.window || 'current window')})</div>${wcBlock}</div>
    </div>
    <div class="cc-grid2">
      <div class="cc-panel"><h3>📊 Market Pulse <span class="gp-badge delayed">DELAYED</span> <a href="#section-markets">View Markets →</a></h3><div class="cc-mkt">${mktCards}</div>${mktOmitted.length ? `<div class="gp-honest" style="margin-top:8px">Not published by the current market feed: ${esc(mktOmitted.join(', '))}. Shown symbols are source-backed.</div>` : ''}</div>
      <div class="cc-panel"><h3>🗄 Source Health <span style="font-weight:400;color:var(--muted);font-size:11px">${fmtInt(healthyCount)} / ${fmtInt(total)} reporting with data</span> <a href="#section-status">View Sources →</a></h3>
        <div class="cc-donut-wrap">${donut(healthyCount, degradedCount, failed, unknownCount)}<div style="flex:1;min-width:0">
          <div style="font-size:11px;display:flex;justify-content:space-between"><span>🟢 Healthy (with data)</span><b>${fmtInt(healthyCount)}</b></div>
          <div style="font-size:11px;display:flex;justify-content:space-between"><span>🟡 Degraded (empty)</span><b>${fmtInt(degradedCount)}</b></div>
          <div style="font-size:11px;display:flex;justify-content:space-between"><span>🔴 Offline / failed</span><b>${fmtInt(failed)}</b></div>
          <div style="font-size:11px;display:flex;justify-content:space-between"><span>⚪ Unknown</span><b>${fmtInt(unknownCount)}</b></div>
        </div></div>
        <div class="gp-tiny gp-muted" style="margin:10px 0 4px;text-transform:uppercase;letter-spacing:.08em">Recent issues</div>${issueRows}</div>
    </div>
    <div class="cc-legend" aria-label="Severity legend"><span><i style="background:var(--blue)"></i>Blue = Informational · Normal activity</span><span><i style="background:var(--amber)"></i>Amber = Watch · Elevated, monitor</span><span><i style="background:var(--red)"></i>Red = Critical · Immediate attention</span><span><i style="background:var(--green)"></i>Green = Healthy · Normal operation</span></div>`;

  el.querySelectorAll('[data-sort]').forEach(btn => btn.addEventListener('click', () => {
    const key = btn.dataset.sort;
    if (regionSort.key === key) regionSort.dir *= -1;
    else { regionSort.key = key; regionSort.dir = key === 'region' ? 1 : -1; }
    renderDashboard();
  }));
  const pill = document.getElementById('commandStatus');
  if (pill) {
    if (!total) { pill.className = 'gp-status-pill'; pill.innerHTML = '<span class="dot"></span><span>Status unknown</span>'; }
    else { pill.className = `gp-status-pill sev-${failed === 0 ? 'healthy' : 'watch'}`; pill.innerHTML = `<span class="dot"></span><span>${failed === 0 ? 'All Systems Operational' : `${failed} failing`}</span>`; }
  }
  const stamp = document.getElementById('dashboardUpdated');
  if (stamp) stamp.textContent = snapshot?.updatedAt ? `Updated ${formatRelativeTime(snapshot.updatedAt)}` : '';
  initDashMap(state);
}

let dashMap = null;
let dashMapFp = '';
function initDashMap(state) {
  try {
    const host = document.getElementById('dashMap');
    if (!host || typeof L === 'undefined') return;
    const markers = Array.isArray(state.mapPoints?.markers) ? state.mapPoints.markers : [];
    const fp = `${state.mapPoints?.updatedAt || ''}|${markers.length}|${state.snapshot?.updatedAt || ''}`;
    if (!dashMap) {
      dashMap = L.map(host, { center: [20, 10], zoom: 2, worldCopyJump: true, preferCanvas: true, zoomControl: false, attributionControl: true, scrollWheelZoom: false });
      const dashBase = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: '© Esri © OpenStreetMap contributors' });
      const dashFallback = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' });
      dashBase.addTo(dashMap);
      dashBase.on('tileerror', () => { try { if (!dashMap.hasLayer(dashFallback)) dashFallback.addTo(dashMap); } catch {} });
      L.control.zoom({ position: 'bottomright' }).addTo(dashMap);
      setTimeout(() => { try { dashMap.invalidateSize(); } catch {} }, 300);
      dashMap.on('zoomend', () => { dashMapFp = ''; initDashMap(state); });
      if (typeof IntersectionObserver !== 'undefined') {
        new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { try { dashMap.invalidateSize(); } catch {} } }), { rootMargin: '200px' }).observe(host);
      }
    }
    if (fp === dashMapFp) return;
    dashMapFp = fp;
    if (dashMap._dashLayer) dashMap.removeLayer(dashMap._dashLayer);
    const layer = L.layerGroup().addTo(dashMap);
    dashMap._dashLayer = layer;
    const colorFor = (m) => {
      const s = `${m.layer || ''} ${m.type || ''}`.toLowerCase();
      if (/cartel|crime|gang/.test(s)) return '#ff8a35';
      if (/hazard|gdacs|earthquake|flood|storm|fire/.test(s)) return '#ffd34d';
      if (/strateg/.test(s)) return '#4d9aff';
      if (/osint|regional|news|report/.test(s)) return '#b08cff';
      return '#ff405f';
    };
    // Deterministic thin sample: every Nth marker so mini-map stays fast and honest.
    const zf = Math.max(1, Math.min(4, (dashMap.getZoom() || 2) / 2));
    const cap = Math.round(350 * zf);
    const step = Math.max(1, Math.floor(markers.length / cap));
    const points = [];
    for (let i = 0; i < markers.length && points.length < cap; i += step) {
      const m = markers[i];
      const lat = Number(m.lat), lon = Number(m.lng);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) continue;
      points.push([lat, lon, colorFor(m)]);
    }
    // Bubbles = clustered real coordinates (no invented region geometry).
    if (typeof L.markerClusterGroup === 'function') {
      const cluster = L.markerClusterGroup({
        maxClusterRadius: 46,
        showCoverageOnHover: false,
        spiderfyOnMaxZoom: false,
        disableClusteringAtZoom: 5,
        iconCreateFunction: (c) => L.divIcon({
          html: `<span>${c.getChildCount()}</span>`,
          className: 'gp-dash-bubble',
          iconSize: L.point(34, 34)
        })
      });
      points.forEach(([lat, lon, color]) => cluster.addLayer(L.circleMarker([lat, lon], { radius: 4, color: '#fff', weight: 1, fillColor: color, fillOpacity: 0.95, interactive: false })));
      cluster.addTo(layer);
    } else {
      points.forEach(([lat, lon, color]) => L.circleMarker([lat, lon], { radius: 4, color: '#fff', weight: 1, fillColor: color, fillOpacity: 0.95, interactive: false }).addTo(layer));
    }
  } catch {}
}
