/** GUI Phase 2 — Alert Queue (Concept 05 theme).
 * Severity is derived only from pipeline-produced fields: conflict
 * `escalation` and live-event `confidence`. Filter counts are real counts.
 * Nothing is fabricated; an empty queue states so honestly. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

let levelFilter = 'all';
let expandedKey = null;
let showAll = false;

const LEVELS = ['critical', 'high', 'medium', 'low'];
const LEVEL_LABEL = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };

function conflictSeverity(conflict) {
  const raw = String(conflict.escalation || '').toUpperCase();
  if (raw === 'CRITICAL') return 'critical';
  if (raw === 'HIGH') return 'high';
  if (raw === 'MODERATE') return 'medium';
  return 'low';
}

function eventSeverity(event) {
  const raw = String(event.confidence || '').toLowerCase();
  if (raw.includes('high') || raw === 'confirmed') return 'critical';
  if (raw.includes('mod') || raw === 'likely') return 'high';
  if (raw.includes('low') || raw === 'limited') return 'medium';
  return 'low';
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
  const rank = { critical: 0, high: 1, medium: 2, low: 3 };
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

  const chips = [`<button class="gp-filter${levelFilter === 'all' ? ' active' : ''}" data-alert-level="all" type="button">All (${counts.all})</button>`]
    .concat(LEVELS.map(level => `<button class="gp-filter${levelFilter === level ? ' active' : ''}" data-alert-level="${level}" type="button">${LEVEL_LABEL[level]} (${counts[level]})</button>`)).join('');

  const rows = shown.map(item => {
    const open = expandedKey === item.key;
    const links = evidenceLinks(item.evidence);
    const initial = esc(String(item.title || 'A').trim().charAt(0).toUpperCase());
    const thumbBg = item.sev === 'critical' ? 'linear-gradient(135deg,#3d0f18,#160a0e)' : item.sev === 'high' ? 'linear-gradient(135deg,#3a2a0c,#14100a)' : item.sev === 'medium' ? 'linear-gradient(135deg,#10294a,#080f1a)' : 'linear-gradient(135deg,#1a2430,#0a0f14)';
    return `<div class="gp-alert sev-${item.sev}"><button class="gp-alert-head" data-alert-toggle="${esc(item.key)}" type="button" aria-expanded="${open}">`
      + `<span class="gp-alert-bar"></span><span class="cc-thumb" style="flex:0 0 44px;width:44px;height:44px;font-size:16px;background:${thumbBg}" aria-hidden="true">${initial}</span><span class="grow" style="min-width:0;flex:1"><span class="title" style="font-weight:600;overflow-wrap:break-word">${esc(item.title)}</span>`
      + `<div class="meta" style="font-size:10px;color:var(--muted-2);margin-top:2px">${esc(item.sub)}${item.sub && item.meta ? ' · ' : ''}${esc(item.meta)}${item.time ? ` · ${esc(formatRelativeTime(item.time))}` : ''}</div></span>`
      + `<span class="gp-sev gp-sev-${item.sev}">${esc(item.sevLabel)}</span></button>`
      + (open ? `<div class="gp-alert-detail">${item.detail ? `<div style="margin-bottom:6px">${esc(item.detail)}</div>` : ''}${links || '<div style="color:var(--muted-2)">No linked evidence records in this snapshot.</div>'}</div>` : '')
      + '</div>';
  }).join('');

  el.innerHTML = `<div class="gp-filter-row" role="group" aria-label="Filter alerts by severity">${chips}</div>`
    + (rows || '<div class="gp-state"><div class="gp-state-title">No alerts at this severity</div><div>Nothing in the current snapshot matches this filter.</div></div>')
    + (visible.length > 12 ? `<button id="alertsMore" class="gp-btn gp-more" type="button">${showAll ? 'Show fewer' : `Show all ${visible.length}`}</button>` : '');

  el.querySelectorAll('[data-alert-level]').forEach(btn => btn.addEventListener('click', () => {
    levelFilter = btn.dataset.alertLevel; expandedKey = null; showAll = false; renderAlerts();
  }));
  el.querySelectorAll('[data-alert-toggle]').forEach(btn => btn.addEventListener('click', () => {
    expandedKey = expandedKey === btn.dataset.alertToggle ? null : btn.dataset.alertToggle; renderAlerts();
  }));
  document.getElementById('alertsMore')?.addEventListener('click', () => { showAll = !showAll; renderAlerts(); });
}
