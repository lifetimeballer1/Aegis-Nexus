/** Command Shell — clock banner, status strip, news ticker, priority badges.
 * Refs 1-3 (dark command-center). All figures derived from canonical state;
 * nothing fabricated. Decorates DOM only; never changes pipeline data. */
import { getState, subscribe } from '../core/state.js';
import { escapeHtml } from '../core/utils.js';

function esc(v) { return escapeHtml(String(v ?? '')); }
function itemTime(i) {
  return i.published || i.publishedAt || i.published_date || i.publishedDate
    || i.time || i.date || i.lastSeen || i.firstSeen || null;
}

function tickClock() {
  const el = document.getElementById('commandClock');
  if (!el) return;
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const local = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  const date = now.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  const utc = `${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())} UTC`;
  el.innerHTML = `<span class="cs-live-dot" aria-hidden="true"></span>`
    + `<span class="cs-time" aria-label="Local time ${local}">${local}</span>`
    + `<span class="cs-date">${esc(date)}</span>`
    + `<span class="cs-utc">${utc}</span>`;
}

function stripCounts(state) {
  const { snapshot, mapData, sourceHealth } = state;
  const conflicts = Array.isArray(snapshot?.conflicts) ? snapshot.conflicts : [];
  const events = Array.isArray(mapData?.events?.events) ? mapData.events.events : [];
  let critical = 0, warning = 0, normal = 0;
  for (const c of conflicts) {
    const e = String(c.escalation || '').toUpperCase();
    if (/CRITICAL/.test(e)) critical++;
    else if (/HIGH|ELEVATED|WATCH/.test(e)) warning++;
    else normal++;
  }
  for (const e of events) {
    const cf = String(e.confidence || '').toLowerCase();
    if (/high|confirmed/.test(cf)) critical++;
    else if (/moderate|medium|likely/.test(cf)) warning++;
    else normal++;
  }
  const summary = sourceHealth?.summary || {};
  const total = Number(summary.total ?? (Array.isArray(sourceHealth?.sources) ? sourceHealth.sources.length : 0));
  const online = Number(summary.onlineWithData ?? summary.online ?? 0);
  const failed = Number(summary.failed ?? 0);
  const ok = total > 0 ? Math.max(0, total - failed) : online;
  return { critical, warning, normal, ok };
}

function renderStrip() {
  const el = document.getElementById('commandStrip');
  if (!el) return;
  const state = getState();
  if (!state.snapshot && !state.mapData && !state.sourceHealth) {
    el.innerHTML = `<div class="cs-strip-seg s-normal"><span>●</span><span>Loading</span><span class="n">—</span></div>`.repeat(4);
    el.setAttribute('aria-label', 'System status loading');
    return;
  }
  const { critical, warning, normal, ok } = stripCounts(state);
  el.innerHTML = `
    <div class="cs-strip-seg s-critical" role="status"><span>●</span><span>Critical</span><span class="n">${critical}</span></div>
    <div class="cs-strip-seg s-warning" role="status"><span>●</span><span>Warning</span><span class="n">${warning}</span></div>
    <div class="cs-strip-seg s-normal" role="status"><span>●</span><span>Normal</span><span class="n">${normal}</span></div>
    <div class="cs-strip-seg s-ok" role="status"><span>●</span><span>OK</span><span class="n">${ok}</span></div>`;
  el.setAttribute('aria-label', `System status: ${critical} critical, ${warning} warning, ${normal} normal, ${ok} sources ok`);
}

function renderTicker() {
  const el = document.getElementById('commandTicker');
  if (!el) return;
  const state = getState();
  const raw = Array.isArray(state.liveArticles) ? state.liveArticles
    : state.liveArticles?.articles || state.snapshot?.stories || [];
  if (!raw.length) {
    el.innerHTML = `<span class="tk-label">News</span><span class="tk-empty">Live feed empty — see Breaking section.</span>`;
    return;
  }
  const items = [...raw]
    .sort((a, b) => new Date(itemTime(b) || 0) - new Date(itemTime(a) || 0))
    .slice(0, 12);
  el.innerHTML = `<span class="tk-label">News</span>` + items.map((s) => {
    const title = s.title || s.headline || 'Untitled';
    return `<a href="#section-breaking" title="${esc(title)}">${esc(String(title).slice(0, 80))}</a>`;
  }).join('');
}

/** Priority badges: P1 critical / P2 watch / P3 info / P4 healthy.
 * Decorates already-rendered .gp-alert heads; idempotent via data attr. */
function decorateAlerts() {
  const heads = document.querySelectorAll('#alertsBody .gp-alert-head:not([data-prio])');
  heads.forEach((head) => {
    head.setAttribute('data-prio', '1');
    const card = head.closest('.gp-alert');
    let label = 'P3', sev = 'info';
    if (card?.classList.contains('sev-critical')) { label = 'P1'; sev = 'critical'; }
    else if (card?.classList.contains('sev-watch') || card?.classList.contains('sev-high')) { label = 'P2'; sev = 'watch'; }
    else if (card?.classList.contains('sev-healthy')) { label = 'P4'; sev = 'healthy'; }
    const badge = document.createElement('span');
    badge.className = `cs-prio prio-${sev}`;
    badge.textContent = label;
    badge.setAttribute('aria-label', `Priority ${label}`);
    const chip = head.querySelector('.gp-sev');
    if (chip) chip.before(badge);
    else head.prepend(badge);
  });
}

export function renderCommandShell() {
  tickClock();
  renderStrip();
  renderTicker();
  decorateAlerts();
}

let clockTimer = null;
export function initCommandShell() {
  renderCommandShell();
  if (clockTimer) clearInterval(clockTimer);
  clockTimer = setInterval(tickClock, 1000);
  subscribe(() => { renderStrip(); renderTicker(); decorateAlerts(); });
  // Alerts render through app.js renderAll; re-decorate after each cycle.
  const mo = new MutationObserver(() => decorateAlerts());
  const alertsBody = document.getElementById('alertsBody');
  if (alertsBody) mo.observe(alertsBody, { childList: true, subtree: true });
}
