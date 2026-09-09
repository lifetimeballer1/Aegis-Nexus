/** GUI Phase 2 — Event Timeline (Concept 05 theme).
 * Points are flattened from the canonical 30-day event-history
 * observations (observedAt timestamps). Period filters admit only
 * records inside the window; undated or future records are excluded.
 * Nothing is fabricated. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

let periodHours = 24;
let userPicked = false;
let selectedIdx = -1;
const PERIODS = [[24, '24H'], [168, '7D'], [720, '30D'], [0, 'ALL']];
const MAX_POINTS = 60;

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

function dotSeverity(confidence) {
  const raw = String(confidence || '').toLowerCase();
  if (raw.includes('high') || raw === 'confirmed') return 'critical';
  if (raw.includes('mod') || raw === 'likely') return 'high';
  if (raw.includes('low') || raw === 'limited') return 'medium';
  return 'low';
}

function parseTime(value) {
  if (!value) return null;
  const date = new Date(String(value).replace(' ', 'T'));
  return Number.isNaN(date.getTime()) ? null : date;
}

function collectPoints(state, hours) {
  const history = state.eventHistory || {};
  const events = history.events || {};
  const now = Date.now();
  const points = [];
  const values = Array.isArray(events) ? events : Object.values(events);
  for (const event of values) {
    if (!event || typeof event !== 'object') continue;
    for (const obs of (event.observations || [])) {
      if (!obs || typeof obs !== 'object') continue;
      const at = parseTime(obs.observedAt);
      if (!at || at.getTime() > now + 120000) continue;
      points.push({
        at,
        title: obs.title || event.title || 'Untitled signal',
        confidence: obs.confidence || event.confidence || '',
        reports: obs.reportCount ?? null,
        sources: obs.sourceCount ?? null,
      });
    }
  }
  const windowHours = hours === undefined ? periodHours : hours;
  const cutoff = windowHours === 0 ? 0 : now - windowHours * 3600000;
  return points.filter(p => p.at.getTime() >= cutoff).sort((a, b) => b.at - a.at);
}

function dayLabel(date) {
  try {
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return ''; }
}

export function renderTimeline() {
  const el = document.getElementById('timelineBody');
  if (!el) return;
  const state = getState();
  if (!state.eventHistory && state.status === 'loading') {
    el.innerHTML = '<div class="gp-state"><div class="gp-spinner"></div><div>Loading event timeline…</div></div>';
    return;
  }
  let points = collectPoints(state);
  if (!userPicked && !points.length) {
    for (const [hours] of PERIODS) {
      const wider = collectPoints(state, hours);
      if (wider.length) { periodHours = hours; points = wider; break; }
    }
  }
  const shown = points.slice(0, MAX_POINTS);
  const chips = PERIODS.map(([hours, label]) =>
    `<button class="gp-filter${periodHours === hours ? ' active' : ''}" data-tl-period="${hours}" type="button">${label}</button>`).join('');

  let lastDay = '';
  const sevName = { critical: 'CRITICAL', high: 'HIGH', medium: 'MEDIUM', low: 'LOW' };
  const rows = shown.map((p, idx) => {
    const day = dayLabel(p.at);
    const header = day !== lastDay ? `<div class="gp-tl-meta" style="margin:4px 0 6px;font-weight:700">${esc(day)}</div>` : '';
    lastDay = day;
    const sev = dotSeverity(p.confidence);
    const meta = [`${p.reports ?? '—'} reports`, `${p.sources ?? '—'} sources`, p.confidence ? `${p.confidence} confidence` : 'confidence ungraded', formatRelativeTime(p.at.toISOString())].join(' · ');
    return `${header}<li class="gp-tl-item"><button data-tl-select="${idx}" type="button" aria-pressed="${selectedIdx === idx}" style="all:unset;cursor:pointer;display:block;width:100%;box-sizing:border-box"><span class="gp-tl-dot sev-${sev}"></span>`
      + `<div class="gp-tl-time">${esc(p.at.toISOString().slice(11, 16))} UTC · <span class="gp-sev gp-sev-${sev}" style="font-size:9px;padding:1px 6px">${sevName[sev] || sev}</span></div>`
      + `<div class="gp-tl-title">${esc(p.title)}</div><div class="gp-tl-meta">${esc(meta)}</div></button></li>`;
  }).join('');

  const sel = selectedIdx >= 0 ? shown[selectedIdx] : null;
  const pane = sel ? `<div class="gp-card" style="margin-top:10px;border-color:var(--line-strong)"><div style="font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:4px">Reading Pane</div>`
    + `<div class="gp-tl-title" style="font-size:13px">${esc(sel.title)}</div>`
    + `<div class="gp-tl-meta">${esc(sel.at.toISOString().slice(0, 16).replace('T', ' '))} UTC · ${sel.reports ?? '—'} reports · ${sel.sources ?? '—'} sources · ${esc(sel.confidence || 'confidence ungraded')}</div></div>` : '';

  el.innerHTML = `<div class="gp-filter-row" role="group" aria-label="Timeline period">${chips}`
    + `<span class="meta" style="align-self:center;font-size:10px;color:var(--muted-2)">Showing ${shown.length} of ${points.length} signals</span></div>`
    + (rows ? `<ol class="gp-timeline">${rows}</ol>${pane}` : '<div class="gp-state"><div class="gp-state-title">No signals in this period</div><div>No dated observations fall inside the selected window.</div></div>');

  el.querySelectorAll('[data-tl-period]').forEach(btn => btn.addEventListener('click', () => {
    periodHours = Number(btn.dataset.tlPeriod); userPicked = true; selectedIdx = -1; renderTimeline();
  }));
  el.querySelectorAll('[data-tl-select]').forEach(btn => btn.addEventListener('click', () => {
    const i = Number(btn.dataset.tlSelect); selectedIdx = selectedIdx === i ? -1 : i; renderTimeline();
  }));
}
