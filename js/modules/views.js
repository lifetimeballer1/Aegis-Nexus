/** Saved Views — named analyst workspace snapshots (Concept 01).
 * Captures cross-module filter state (alert severity, timeline period or
 * custom range, brief category) into localStorage; applying a view calls
 * each module's own setter so rendering stays canonical. Map layer prefs
 * already persist separately. Device-only, no backend. */
import { getAlertLevel, setAlertLevel } from './alerts.js';
import { getTimelineView, setTimelineView } from './timeline.js';
import { getBriefCategory, setBriefCategory } from './briefings.js';
import { escapeHtml } from '../core/utils.js';

export const VIEWS_KEY = 'gp.savedViews.v1';

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

function loadViews() {
  try {
    const raw = JSON.parse(localStorage.getItem(VIEWS_KEY) || '[]');
    return Array.isArray(raw) ? raw.filter(v => v && typeof v === 'object') : [];
  } catch { return []; }
}

function saveViews(views) {
  try { localStorage.setItem(VIEWS_KEY, JSON.stringify(views)); } catch {}
}

function describe(view) {
  const parts = [];
  if (view.alertLevel && view.alertLevel !== 'all') parts.push(`alerts: ${view.alertLevel}`);
  const tl = view.timeline || {};
  if (tl.custom && (tl.from || tl.to)) parts.push(`timeline: ${tl.from || '…'} → ${tl.to || '…'}`);
  else if (tl.period === 0) parts.push('timeline: ALL');
  else if (Number.isFinite(Number(tl.period))) parts.push(`timeline: last ${Number(tl.period) >= 168 ? `${Number(tl.period) / 168}D` : `${Number(tl.period)}H`}`);
  if (view.briefCategory && view.briefCategory !== 'all') parts.push(`brief: ${view.briefCategory}`);
  return parts.join(' · ') || 'default filters';
}

export function renderViews() {
  const el = document.getElementById('viewsBody');
  if (!el) return;
  const views = loadViews();
  const rows = views.map(v => `<div class="gp-dash-row"><div class="grow"><div class="title">${esc(v.name || 'Untitled view')}</div>`
    + `<div class="meta">${esc(describe(v))}</div></div>`
    + `<div style="display:flex;gap:6px"><button class="gp-btn" data-view-apply="${esc(v.id)}" type="button">Apply</button>`
    + `<button class="gp-btn" data-view-del="${esc(v.id)}" type="button">Delete</button></div></div>`).join('');

  el.innerHTML = `<div class="gp-dash-panel"><h3>📌 Saved Views <span style="font-weight:400;color:var(--muted);font-size:10px">filter snapshots · this device only</span></h3>`
    + (rows ? `<div class="gp-dash-list">${rows}</div>` : '<div class="meta">No saved views yet — set filters anywhere, then save them here.</div>')
    + `<div style="display:flex;gap:6px;margin-top:8px"><input id="viewName" class="gp-map-search" type="text" aria-label="Name this view" placeholder="Name this view…" maxlength="60" style="flex:1">`
    + `<button class="gp-btn" data-view-save type="button">Save current filters</button></div></div>`;

  el.querySelector('[data-view-save]')?.addEventListener('click', () => {
    const name = (el.querySelector('#viewName')?.value || '').trim() || `View ${views.length + 1}`;
    const list = loadViews();
    list.push({
      id: `view-${Date.now().toString(36)}`,
      name,
      alertLevel: getAlertLevel(),
      timeline: getTimelineView(),
      briefCategory: getBriefCategory(),
      updatedAt: new Date().toISOString(),
    });
    saveViews(list); renderViews();
  });
  el.querySelectorAll('[data-view-apply]').forEach(b => b.addEventListener('click', () => {
    const v = loadViews().find(x => x.id === b.dataset.viewApply);
    if (!v) return;
    setAlertLevel(v.alertLevel || 'all');
    setTimelineView(v.timeline || { period: 24 });
    setBriefCategory(v.briefCategory || 'all');
  }));
  el.querySelectorAll('[data-view-del]').forEach(b => b.addEventListener('click', () => {
    saveViews(loadViews().filter(x => x.id !== b.dataset.viewDel));
    renderViews();
  }));
}
