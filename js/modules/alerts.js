/** GUI Phase 2 — Alert Queue (Concept 05 theme).
 * Severity is derived only from pipeline-produced fields: conflict
 * `escalation` and live-event `confidence`. Filter counts are real counts.
 * Nothing is fabricated; an empty queue states so honestly. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';
import { confidenceSeverity, escalationSeverity } from '../core/severity.js';
import { addSupportingToDraft } from './briefings.js';

let levelFilter = 'all';
let expandedKey = null;
let showAll = false;

const LEVEL_KEY = 'gp.alertLevel.v1';
try {
  const saved = localStorage.getItem(LEVEL_KEY);
  if (saved === 'all' || LEVELS.includes(saved)) levelFilter = saved;
} catch {}
function persistLevel() {
  try { localStorage.setItem(LEVEL_KEY, levelFilter); } catch {}
}

const ACK_KEY = 'gp.alertAck.v1';
function loadAck() {
  try { const raw = JSON.parse(localStorage.getItem(ACK_KEY) || '{}'); return raw && typeof raw === 'object' ? raw : {}; }
  catch { return {}; }
}
let acked = loadAck();
function saveAck() {
  try { localStorage.setItem(ACK_KEY, JSON.stringify(acked)); } catch {}
}
/* Ack entries are {at, title}; legacy string entries (ISO only) still read. */
function ackTime(key) {
  const v = acked[key];
  if (!v) return null;
  return typeof v === 'string' ? v : (v.at || null);
}

const LEVELS = ['critical', 'watch', 'info', 'healthy'];
const LEVEL_LABEL = { critical: 'Critical', watch: 'Watch', info: 'Info', healthy: 'Healthy' };

function conflictSeverity(conflict) {
  return escalationSeverity(conflict.escalation);
}

function eventSeverity(event) {
  return confidenceSeverity(event.confidence);
}

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

function evidenceLinks(entries) {
  const out = [];
  for (const entry of (entries || []).slice(0, 4)) {
    if (!entry) continue;
    if (typeof entry === 'string') {
      if (/^https?:\/\//i.test(entry)) out.push(`<div><a href="${esc(entry)}" target="_blank" rel="noopener noreferrer">Open source ↗</a></div>`);
      else if (entry.trim()) out.push(`<div>${esc(entry.trim())}</div>`);
      continue;
    }
    const title = entry.title || entry.name || entry.source || '';
    const url = entry.url || entry.href || entry.link || '';
    if (/^https?:\/\//i.test(url)) out.push(`<div><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(title || 'Open source ↗')}</a></div>`);
    else if (String(title).trim()) out.push(`<div>${esc(String(title).trim())}</div>`);
  }
  return out.join('');
}

function collectItems(state) {
  const { snapshot, mapData } = state;
  const items = [];
  for (const c of (snapshot?.conflicts || [])) {
    if (!c || typeof c !== 'object') continue;
    items.push({
      key: `conflict:${c.id || c.name}`,
      kind: 'conflict',
      title: c.name || c.id || 'Unnamed conflict',
      sub: [c.region, c.category, c.status].filter(Boolean).join(' · '),
      detail: c.recent || c.analysis || '',
      meta: `${c.signalCount ?? '—'} signals · ${c.sourceCount ?? '—'} sources · confidence ${c.confidence || 'ungraded'}`,
      time: c.lastSignal || snapshot?.updatedAt || null,
      sev: conflictSeverity(c),
      sevLabel: c.escalation ? `Escalation: ${c.escalation}` : 'Escalation: ungraded',
      evidence: c.signals || [],
    });
  }
  const events = Array.isArray(mapData?.events?.events) ? mapData.events.events : [];
  for (const e of events) {
    if (!e || typeof e !== 'object') continue;
    items.push({
      key: `event:${e.id || e.title}`,
      kind: 'event',
      title: e.title || 'Untitled event',
      sub: [(e.category || '').toUpperCase(), (e.anchors || []).slice(0, 3).join(', ')].filter(Boolean).join(' · '),
      detail: '',
      meta: `${e.reportCount ?? '—'} reports · ${e.sourceCount ?? '—'} source domains · confidence ${e.confidence || 'ungraded'}`,
      time: e.lastSeen || e.firstSeen || null,
      sev: eventSeverity(e),
      sevLabel: `Confidence: ${e.confidence || 'ungraded'}`,
      evidence: [...(e.reports || []), ...(e.urls || [])],
    });
  }
  const rank = { critical: 0, watch: 1, info: 2, healthy: 3 };
  items.sort((a, b) => (rank[a.sev] - rank[b.sev]) || (new Date(b.time || 0) - new Date(a.time || 0)));
  return items;
}

export function renderAlerts() {
  const el = document.getElementById('alertsBody');
  if (!el) return;
  const state = getState();
  const { snapshot, mapData } = state;
  if (!snapshot && !mapData) {
    el.innerHTML = state.status === 'loading'
      ? '<div class="gp-state"><div class="gp-spinner"></div><div>Loading alert queue…</div></div>'
      : '<div class="gp-state"><div class="gp-state-title">Alert queue unavailable</div><div>Core data failed to load.</div></div>';
    return;
  }
  const items = collectItems(state);
  const counts = { all: items.length };
  for (const level of LEVELS) counts[level] = items.filter(i => i.sev === level).length;
  const visible = levelFilter === 'all' ? items : items.filter(i => i.sev === levelFilter);
  const shown = showAll ? visible : visible.slice(0, 12);

  const chips = [`<button class="gp-filter${levelFilter === 'all' ? ' active' : ''}" data-alert-level="all" type="button" aria-pressed="${levelFilter === 'all'}">All (${counts.all})</button>`]
    .concat(LEVELS.map(level => `<button class="gp-filter${levelFilter === level ? ' active' : ''}" data-alert-level="${level}" type="button" aria-pressed="${levelFilter === level}">${LEVEL_LABEL[level]} (${counts[level]})</button>`)).join('');

  const rowsByGroup = (list) => list.map(item => {
    const open = expandedKey === item.key;
    const links = evidenceLinks(item.evidence);
    const ackAt = ackTime(item.key);
    const initial = esc(String(item.title || 'A').trim().charAt(0).toUpperCase());
    const thumbBg = item.sev === 'critical' ? 'linear-gradient(135deg,#3d0f18,#160a0e)' : item.sev === 'watch' ? 'linear-gradient(135deg,#3a2a0c,#14100a)' : item.sev === 'healthy' ? 'linear-gradient(135deg,#0d2b1c,#081009)' : 'linear-gradient(135deg,#10294a,#080f1a)';;
    return `<div class="gp-alert sev-${item.sev}"><button class="gp-alert-head" data-alert-toggle="${esc(item.key)}" type="button" aria-expanded="${open}" aria-label="${esc(item.title)} — ${esc(item.sevLabel)}">`
      + `<span class="gp-alert-bar" aria-hidden="true"></span><span class="cc-thumb gp-alert-thumb" style="flex:0 0 36px;width:36px;height:36px;font-size:14px;background:${thumbBg}" aria-hidden="true">${initial}</span><span class="grow" style="min-width:0;flex:1"><span class="title" style="font-weight:600;overflow-wrap:break-word">${esc(item.title)}</span>`
      + `<div class="meta" style="font-size:10px;color:var(--muted-2);margin-top:2px">${esc(item.sub)}${item.sub && item.meta ? ' · ' : ''}${esc(item.meta)}${item.time ? ` · ${esc(formatRelativeTime(item.time))}` : ''}${ackAt ? ` · ✓ acknowledged ${esc(formatRelativeTime(ackAt))}` : ''}</div></span>`
      + `<span class="gp-sev gp-sev-${item.sev}">${esc(item.sevLabel)}</span></button>`
      + (open ? `<div class="gp-alert-detail">${item.detail ? `<div style="margin-bottom:6px">${esc(item.detail)}</div>` : ''}${links || '<div style="color:var(--muted-2)">No linked evidence records in this snapshot.</div>'}`
        + `<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap"><button class="gp-btn" data-alert-ack="${esc(item.key)}" type="button" title="Stored only on this device">${ackAt ? 'Clear acknowledgement' : 'Acknowledge'}</button><button class="gp-btn" data-brief-add="${esc(item.key)}" data-brief-title="${esc(item.title)}" type="button" title="Saved to the active briefing draft on this device">Add to briefing</button></div></div>` : '')
      + '</div>';
  }).join('');

  /* Grouping visuals: when viewing All, cluster rows under severity group
   * headers (rank order, real counts); a filtered view stays a flat list. */
  const rows = levelFilter === 'all'
    ? LEVELS.map(level => {
        const group = shown.filter(i => i.sev === level);
        if (!group.length) return '';
        return `<div class="gp-alert-group" role="group" aria-label="${LEVEL_LABEL[level]} alerts, ${group.length} shown of ${counts[level]} total">`
          + `<div class="gp-micro-label gp-alert-group-head" aria-hidden="true">${LEVEL_LABEL[level]} · ${group.length}/${counts[level]}</div>`
          + rowsByGroup(group) + '</div>';
      }).join('')
    : rowsByGroup(shown);

  const ackKeys = Object.keys(acked);
  const liveKeys = new Set(items.map(i => i.key));
  const unackedCritical = items.filter(i => (i.sev === 'critical' || i.sev === 'watch') && !acked[i.key]).length;
  const ackRows = ackKeys.map(k => {
    const v = acked[k];
    const title = (v && typeof v === 'object' && v.title) ? v.title : (items.find(i => i.key === k)?.title || k);
    const at = ackTime(k);
    return `<div class="gp-dash-row"><div class="grow"><div class="title" style="font-size:11px">${esc(title)}</div>`
      + `<div class="meta">${at ? `acknowledged ${esc(formatRelativeTime(at))} · ` : ''}${liveKeys.has(k) ? 'still in queue' : 'rotated out of queue'}</div></div>`
      + `<button class="gp-btn" data-ack-clear="${esc(k)}" type="button">Clear</button></div>`;
  }).join('');

  el.innerHTML = `<div class="gp-filter-row" role="group" aria-label="Filter alerts by severity">${chips}</div>`
    + (rows || '<div class="gp-state"><div class="gp-state-title">No alerts at this severity</div><div>Nothing in the current snapshot matches this filter.</div></div>')
    + (visible.length > 12 ? `<button id="alertsMore" class="gp-btn gp-more" type="button">${showAll ? 'Show fewer' : `Show all ${visible.length}`}</button>` : '')
    + `<div class="gp-dash-panel" style="margin-top:8px"><h3>Acknowledgement Status <span style="font-weight:400;color:var(--muted);font-size:10px">${ackKeys.length} acknowledged · ${unackedCritical} unacked critical/watch · this device only</span></h3>`
    + (ackRows ? `<div class="gp-dash-list">${ackRows}</div>` : '<div class="meta">Nothing acknowledged yet — expand an alert to acknowledge it.</div>') + `</div>`;

  el.querySelectorAll('[data-alert-level]').forEach(btn => btn.addEventListener('click', () => {
    levelFilter = btn.dataset.alertLevel; expandedKey = null; showAll = false; persistLevel(); renderAlerts();
  }));
  el.querySelectorAll('[data-alert-toggle]').forEach(btn => btn.addEventListener('click', () => {
    expandedKey = expandedKey === btn.dataset.alertToggle ? null : btn.dataset.alertToggle; renderAlerts();
  }));
  el.querySelectorAll('[data-alert-ack]').forEach(btn => btn.addEventListener('click', () => {
    const key = btn.dataset.alertAck;
    if (acked[key]) delete acked[key];
    else {
      const item = items.find(i => i.key === key);
      acked[key] = { at: new Date().toISOString(), title: item ? item.title : key };
    }
    saveAck(); renderAlerts();
  }));
  el.querySelectorAll('[data-brief-add]').forEach(btn => btn.addEventListener('click', () => {
    addSupportingToDraft({ kind: 'alert', key: btn.dataset.briefAdd, label: btn.dataset.briefTitle || btn.dataset.briefAdd });
    btn.textContent = 'Added ✓';
  }));
  document.getElementById('alertsMore')?.addEventListener('click', () => { showAll = !showAll; renderAlerts(); });
  el.querySelectorAll('[data-ack-clear]').forEach(btn => btn.addEventListener('click', () => {
    delete acked[btn.dataset.ackClear]; saveAck(); renderAlerts();
  }));
}

export function getAlertLevel() { return levelFilter; }
export function setAlertLevel(level) {
  if (level !== 'all' && !LEVELS.includes(level)) return;
  levelFilter = level; expandedKey = null; showAll = false; persistLevel(); renderAlerts();
}
