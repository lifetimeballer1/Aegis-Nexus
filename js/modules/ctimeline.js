/** TRACK-B — Command-Timeline section (Concepts 01/05/06 refs).
 * Fixtures-backed Timeline builder. Self-contained on purpose: zero
 * imports, so this section keeps painting even if a core/live module
 * fails. Single data source: fetch('data/gui-fixtures.json').
 * Panels are individually guarded — one bad panel can never blank
 * the others. Nothing is fabricated: every figure comes from the
 * frozen fixtures; absent fields render honest empty states.
 * House patterns borrowed (read-only) from briefings.js / alerts.js /
 * timeline.js: gp-* primitives, filter chips, expand-in-place rows.
 * Vanilla JS only — no build step, no node dependency. */

const FIXTURES_URL = 'data/gui-fixtures.json';
const REFRESH_S = 60;
const HOST_ID = 'ctimelineBody';

let cache = null;
let booted = false;
let timerId = null;
let remainS = REFRESH_S;
let paused = false;
let expanded = -1;
let query = '';

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c));
}

function rel(iso) {
  if (!iso) return 'time unknown';
  const t = new Date(String(iso).replace(' ', 'T')).getTime();
  if (!Number.isFinite(t)) return 'time unknown';
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function norm(s) {
  return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function sevOf(confidence, fallback) {
  const c = String(confidence || '').toLowerCase();
  if (c === 'high' || c === 'confirmed' || c === 'critical') return 'critical';
  if (c === 'moderate' || c === 'likely' || c === 'watch') return 'watch';
  if (c === 'low' || c === 'limited' || c === 'info') return 'info';
  if (c === 'healthy' || c === 'stable') return 'healthy';
  return fallback || 'info';
}

async function loadFixtures() {
  const res = await fetch(FIXTURES_URL, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`fixtures HTTP ${res.status}`);
  return res.json();
}

function matchContext(title, fx) {
  const n = norm(title);
  if (!n) return null;
  const pools = [
    ...(Array.isArray(fx?.headlines?.events) ? fx.headlines.events : []),
    ...(Array.isArray(fx?.headlines?.topDevelopments) ? fx.headlines.topDevelopments : []),
  ];
  for (const item of pools) {
    if (!item || typeof item !== 'object') continue;
    const m = norm(item.title);
    if (!m) continue;
    if (n.includes(m.slice(0, 24)) || m.includes(n.slice(0, 24))) return item;
  }
  return null;
}

/* ---------- panels (each returns HTML, never throws to caller) ---------- */

function headlinesPanel(fx) {
  const stories = Array.isArray(fx?.headlines?.stories) ? fx.headlines.stories.slice(0, 4) : [];
  const frozen = fx?.meta?.frozenAt || '';
  if (!stories.length) return '<div class="gp-state"><div class="gp-state-title">No headlines in fixtures</div><div>frozen snapshot carries no stories.</div></div>';
  const q = norm(query);
  const cards = stories.map((s, i) => ({ s, i })).filter(({ s }) => {
    if (!q) return true;
    return norm(`${s.title} ${s.source} ${s.type}`).includes(q);
  });
  if (!cards.length) return `<div class="gp-state"><div class="gp-state-title">No headlines match “${esc(query)}”</div><div>Clear the search to see all four cards.</div></div>`;
  return cards.map(({ s, i }) => {
    const num = String(i + 1).padStart(2, '0');
    const open = expanded === i;
    const ctx = matchContext(s.title, fx);
    const brief = open ? (
      '<div class="ct-brief">'
      + `<div class="ct-brief-row"><span class="ct-tag">${esc(ctx?.category || s.type || 'general')}</span>`
      + `<span class="gp-sev gp-sev-${sevOf(ctx?.confidence, 'info')}">${esc(ctx?.confidence || 'ungraded')}</span>`
      + (ctx?.reports != null ? `<span class="ct-meta">${esc(ctx.reports)} reports</span>` : '') + '</div>'
      + `<div>${esc(s.title)}</div>`
      + `<div class="ct-frozen-note">Frozen brief · source ${esc(s.source || 'unknown')} · snapshot ${esc(rel(frozen))} · no live data.</div>`
      + '</div>'
    ) : '';
    return `<article class="ct-hl"><div class="ct-hl-top"><span class="ct-num">${num}</span>`
      + `<span class="ct-tag">${esc(s.type || 'general')}</span></div>`
      + `<div class="ct-hl-title">${esc(s.title || 'Untitled')}</div>`
      + `<div class="ct-hl-meta">${esc(s.source || 'unknown source')} · as of ${esc(rel(frozen))}</div>`
      + `<div class="ct-hl-actions"><button class="gp-btn" data-ct-expand="${i}" type="button" aria-expanded="${open}">${open ? 'CLOSE BRIEF' : 'READ FULL BRIEFING'}</button></div>`
      + brief + '</article>';
  }).join('');
}

function tensionPanel(fx) {
  const t = fx?.tension;
  if (!t || typeof t.index !== 'number') return '<div class="gp-state"><div class="gp-state-title">Tension unavailable</div><div>fixtures carry no tension index.</div></div>';
  const delta = Number(t.delta);
  const deltaHtml = !Number.isFinite(delta) || delta === 0
    ? '<span class="ct-delta ct-delta-na">— no change</span>'
    : `<span class="ct-delta ${delta > 0 ? 'ct-delta-up' : 'ct-delta-down'}">${delta > 0 ? '▲' : '▼'} ${Math.abs(delta)}</span>`;
  const level = t.earlyWarning?.level || 'WATCH';
  const breakdown = t.breakdown && typeof t.breakdown === 'object' ? t.breakdown : {};
  const drivers = Object.entries(breakdown)
    .filter(([, v]) => Number.isFinite(Number(v)))
    .map(([k, v]) => ({ label: k, value: Number(v) }))
    .sort((a, b) => b.value - a.value);
  const bars = drivers.length ? drivers.map((d) => {
    const cls = d.value >= 46 ? 'crit' : d.value >= 40 ? 'hot' : '';
    return `<div class="ct-bar-row"><span class="ct-bar-label">${esc(d.label)}</span>`
      + `<span class="ct-bar-val">${d.value} <span class="ct-delta ct-delta-na" title="Per-driver deltas are not in the frozen fixtures">—</span></span>`
      + `<span class="ct-bar-track"><span class="ct-bar-fill ${cls}" style="width:${Math.max(0, Math.min(100, d.value))}%"></span></span></div>`;
  }).join('') : '<div class="gp-state"><div class="gp-state-title">No driver breakdown</div><div>fixtures carry no per-driver values.</div></div>';
  return `<div class="ct-tension-hero"><span class="ct-tension-score">${t.index}</span>`
    + `<span class="ct-tension-side">${deltaHtml}<span class="gp-sev gp-sev-${sevOf(level, 'watch')}">${esc(level)}</span></span></div>`
    + `<span class="ct-sub">6 drivers · strongest ${esc(t.earlyWarning?.strongestDriver || '—')} · per-driver deltas not in frozen fixtures</span>`
    + bars;
}

function mixPanel(fx) {
  const mix = fx?.domainMix && typeof fx.domainMix === 'object' ? fx.domainMix : {};
  const rows = Object.entries(mix)
    .filter(([, v]) => Number.isFinite(Number(v)) && Number(v) > 0)
    .map(([k, v]) => ({ label: k, value: Number(v) }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
  if (!rows.length) return '<div class="gp-state"><div class="gp-state-title">Domain mix unavailable</div><div>fixtures carry no category counts.</div></div>';
  const max = rows[0].value;
  return `<span class="ct-sub">Headlines by category · snapshot mix · top ${rows.length}</span>`
    + rows.map((r) => `<div class="ct-mix-row"><span class="ct-mix-label" title="${esc(r.label)}">${esc(r.label)}</span>`
      + `<span class="ct-bar-track"><span class="ct-bar-fill" style="width:${Math.max(2, Math.round((r.value / max) * 100))}%"></span></span>`
      + `<span class="ct-mix-count">${r.value.toLocaleString('en-US')}</span></div>`).join('');
}

function alertsPanel(fx) {
  const a = fx?.alerts;
  if (!a || typeof a !== 'object') return '<div class="gp-state"><div class="gp-state-title">Alert feed unavailable</div><div>fixtures carry no alerts block.</div></div>';
  const ew = a.earlyWarning || {};
  const tc = a.topConflict || {};
  const errs = Array.isArray(a.breakingErrors) ? a.breakingErrors : [];
  const failed = Array.isArray(a.failedSources) ? a.failedSources : [];
  const rows = [];
  if (tc.name) rows.push(`<div class="ct-feed-row ct-sev-critical"><div class="ct-feed-title">${esc(tc.name)}</div>`
    + `<div class="ct-feed-meta">Escalation ${esc(tc.escalation || 'ungraded')} · ${esc(tc.signals ?? '—')} signals <span class="gp-sev gp-sev-critical">PRIORITY</span></div></div>`);
  if (ew.level) rows.push(`<div class="ct-feed-row ct-sev-watch"><div class="ct-feed-title">Early warning — ${esc(ew.level)}</div>`
    + `<div class="ct-feed-meta">Score ${esc(ew.score ?? '—')} · ${esc(ew.direction || '—')} · strongest driver ${esc(ew.strongestDriver || '—')} (${esc(ew.strongestDriverScore ?? '—')})</div></div>`);
  for (const e of errs) rows.push(`<div class="ct-feed-row ct-sev-info"><div class="ct-feed-title">Breaking window (${esc(a.breakingWindow || '—')}) throttled</div>`
    + `<div class="ct-feed-meta">${esc(e)} · retry backs off automatically</div></div>`);
  if (!rows.length) rows.push('<div class="gp-state"><div class="gp-state-title">Feed quiet</div><div>No priority items in this snapshot.</div></div>');
  const fails = failed.length ? `<details class="ct-details"><summary>Degraded sources (${failed.length}) — failover active</summary>`
    + failed.map((f) => `<div class="ct-fail-src">${esc(f)}</div>`).join('') + '</details>' : '';
  return `<div class="ct-feed-head"><span class="ct-src-badge">● FIXTURES-BACKED · WORKING</span>`
    + `<button class="gp-btn" data-ct-retry type="button">RETRY</button></div>`
    + rows.join('') + fails;
}

/* ---------- shell + wiring ---------- */

function paintPanels(host) {
  if (!cache) return;
  const set = (id, html) => {
    const el = host.querySelector(`#${id}`);
    if (el) el.innerHTML = html;
  };
  try { set('ctHeadlines', headlinesPanel(cache)); } catch (e) { set('ctHeadlines', panelError(e)); }
  try { set('ctTension', tensionPanel(cache)); } catch (e) { set('ctTension', panelError(e)); }
  try { set('ctMix', mixPanel(cache)); } catch (e) { set('ctMix', panelError(e)); }
  try { set('ctAlerts', alertsPanel(cache)); } catch (e) { set('ctAlerts', panelError(e)); }
  const meta = host.querySelector('#ctMeta');
  if (meta) meta.textContent = `Frozen ${rel(cache?.meta?.frozenAt)} · tension ${cache?.tension?.index ?? '—'} · ${cache?.signals?.stories ?? '—'} stories`;
}

function panelError(err) {
  return `<div class="gp-state"><div class="gp-state-title">Panel render failed</div><div>${esc(err?.message || err)}</div></div>`;
}

function shellHtml() {
  return `<div class="ct-head"><h3 class="ct-title">Command Timeline</h3><span class="ct-meta" id="ctMeta">loading…</span></div>`
    + `<div class="ct-toolbar" role="search"><input class="ct-search" id="ctSearch" type="search" placeholder="Filter headlines…" aria-label="Filter headlines" value="${esc(query)}">`
    + `<button class="ct-countdown" id="ctCountdown" type="button" aria-label="Auto-refresh countdown, activate to pause or resume">↻ --:--</button></div>`
    + `<div class="ct-grid"><div class="ct-panel" aria-label="Headlines"><h3>Headlines</h3><div id="ctHeadlines"><div class="gp-state"><div class="gp-spinner"></div><div>Loading headlines…</div></div></div></div>`
    + `<div class="ct-grid ct-grid-2"><div class="ct-panel" aria-label="Tension deep dive"><h3>Tension deep dive</h3><div id="ctTension"></div></div>`
    + `<div class="ct-panel" aria-label="Domain mix"><h3>Domain mix</h3><div id="ctMix"></div></div></div>`
    + `<div class="ct-panel" aria-label="Alerts and priority feed"><h3>Alerts &amp; priority feed</h3><div id="ctAlerts"></div></div></div>`;
}

function wire(host) {
  host.addEventListener('click', (ev) => {
    const exp = ev.target.closest('[data-ct-expand]');
    if (exp) {
      const i = Number(exp.dataset.ctExpand);
      expanded = expanded === i ? -1 : i;
      const box = host.querySelector('#ctHeadlines');
      if (box && cache) { try { box.innerHTML = headlinesPanel(cache); } catch (e) { box.innerHTML = panelError(e); } }
      return;
    }
    if (ev.target.closest('[data-ct-retry]')) {
      refresh(host);
      return;
    }
    if (ev.target.closest('#ctCountdown')) {
      paused = !paused;
      tick(host);
    }
  });
  host.addEventListener('input', (ev) => {
    if (ev.target && ev.target.id === 'ctSearch') {
      query = ev.target.value;
      const box = host.querySelector('#ctHeadlines');
      if (box && cache) { try { box.innerHTML = headlinesPanel(cache); } catch (e) { box.innerHTML = panelError(e); } }
    }
  });
}

async function refresh(host) {
  try {
    cache = await loadFixtures();
    paintPanels(host);
  } catch (err) {
    host.innerHTML = `<div class="gp-state"><div class="gp-state-title">Timeline unavailable</div>`
      + `<div>${esc(err?.message || err)} — fixtures not reachable.</div>`
      + `<div style="margin-top:8px"><button class="gp-btn" data-ct-boot-retry type="button">RETRY</button></div></div>`;
    const btn = host.querySelector('[data-ct-boot-retry]');
    if (btn) btn.addEventListener('click', () => boot(host, true));
    return;
  }
  remainS = REFRESH_S;
  tick(host);
}

function fmtClock(s) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function tick(host) {
  const el = host.querySelector ? host.querySelector('#ctCountdown') : null;
  if (el) el.textContent = paused ? `❚❚ ${fmtClock(remainS)}` : `↻ ${fmtClock(remainS)}`;
}

function startTimer(host) {
  if (timerId) return;
  timerId = setInterval(() => {
    if (paused || !cache) return;
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
    remainS -= 1;
    if (remainS <= 0) { refresh(host); return; }
    tick(host);
  }, 1000);
}

function boot(host, force) {
  if (!host) return;
  if (booted && !force) return;
  booted = true;
  if (!force) { host.innerHTML = shellHtml(); wire(host); }
  else { host.innerHTML = shellHtml(); query = ''; expanded = -1; }
  const input = (typeof document !== 'undefined') ? host.querySelector('#ctSearch') : null;
  if (input && document.activeElement !== input) input.value = query;
  refresh(host);
  startTimer(host);
}

export function renderCtimeline(hostOrId) {
  const host = typeof hostOrId === 'string'
    ? document.getElementById(hostOrId)
    : hostOrId || document.getElementById(HOST_ID);
  if (!host) return;
  boot(host, booted);
}

/* App-convention alias (safeRender looks for render + capitalised name). */
export function renderCTimeline(hostOrId) {
  return renderCtimeline(hostOrId);
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById(HOST_ID)) renderCtimeline();
  });
}
