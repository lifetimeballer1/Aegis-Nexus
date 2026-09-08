/** GUI Phase 7 — Intelligence Briefings workspace.
 * Renders the canonical deterministic brief (data/intelligence_brief.json
 * with headline/topDevelopments/watchlist/methodology/freshness) through
 * core state. Priority/severity derive only from artifact fields
 * (breaking, confidence, watchlist level); category filters show real
 * counts. Nothing is fabricated: missing data renders honest
 * loading/empty states. Severity follows the shared language. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

let categoryFilter = 'all';
let showAllDevelopments = false;

const DEV_PAGE = 8;

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

function developmentSeverity(dev) {
  if (dev.breaking) return 'critical';
  const raw = String(dev.confidence || '').toLowerCase();
  if (raw.includes('high') || raw === 'confirmed') return 'critical';
  if (raw.includes('mod') || raw === 'likely') return 'high';
  if (raw.includes('low') || raw === 'limited') return 'medium';
  return 'low';
}

function watchSeverity(level) {
  const raw = String(level || '').toUpperCase();
  if (raw === 'CRITICAL') return 'critical';
  if (raw === 'HIGH' || raw === 'ELEVATED' || raw === 'WATCH') return 'watch';
  return 'info';
}

function deltaArrow(delta) {
  const n = Number(delta);
  if (!Number.isFinite(n) || n === 0) return '<span class="gp-trend-flat">—</span>';
  return n > 0 ? '<span class="gp-trend-up">▲</span>' : '<span class="gp-trend-down">▼</span>';
}

export function renderBriefings() {
  const el = document.getElementById('briefingsBody');
  if (!el) return;
  const state = getState();
  const brief = state.intelligenceBrief || null;
  if (!brief && state.status === 'loading') {
    el.innerHTML = '<div class="gp-state"><div class="gp-spinner"></div><div>Loading intelligence brief…</div></div>';
    return;
  }
  if (!brief || !Array.isArray(brief.topDevelopments)) {
    el.innerHTML = '<div class="gp-state"><div class="gp-state-title">Brief unavailable</div><div>The intelligence brief failed to load. Check source health below.</div></div>';
    return;
  }
  const developments = brief.topDevelopments.filter(d => d && typeof d === 'object');
  const watchlist = Array.isArray(brief.watchlist) ? brief.watchlist.filter(w => w && typeof w === 'object') : [];
  const categories = [...new Set(developments.map(d => String(d.category || 'general')))].sort();
  const visible = (categoryFilter === 'all' ? developments : developments.filter(d => String(d.category || 'general') === categoryFilter));
  const shown = showAllDevelopments ? visible : visible.slice(0, DEV_PAGE);
  const freshness = brief.freshness || {};

  const chips = [`<button class="gp-filter${categoryFilter === 'all' ? ' active' : ''}" data-brief-filter="all" type="button">All (${developments.length})</button>`]
    .concat(categories.map(c => `<button class="gp-filter${categoryFilter === c ? ' active' : ''}" data-brief-filter="${esc(c)}" type="button">${esc(c)} (${developments.filter(d => String(d.category || 'general') === c).length})</button>`)).join('');

  const devRows = shown.map(dev => {
    const sev = developmentSeverity(dev);
    const meta = [`${dev.reportCount ?? '—'} reports`, `${dev.independentSourceCount ?? '—'} independent sources`, `confidence ${dev.confidence || 'ungraded'}`];
    if (dev.lastSeen) meta.push(formatRelativeTime(dev.lastSeen));
    const sources = Array.isArray(dev.sources) ? dev.sources.slice(0, 4).join(', ') : '';
    return `<div class="gp-brief-dev sev-${sev}"><span class="gp-alert-bar"></span><div class="grow">`
      + `<div class="title">${esc(dev.title || 'Untitled development')}</div>`
      + `<div class="meta">${esc(meta.join(' · '))}${sources ? ` · ${esc(sources)}` : ''}</div></div>`
      + `<span class="gp-sev gp-sev-${sev}">${dev.breaking ? 'Breaking' : esc(dev.confidence || 'ungraded')}</span></div>`;
  }).join('');

  const watchRows = watchlist.slice(0, 10).map(w => {
    const sev = watchSeverity(w.level);
    const factors = Array.isArray(w.topFactors) ? w.topFactors.slice(0, 3).map(f => `${f.label || ''}${f.delta !== undefined && f.delta !== null ? ` (${Number(f.delta) > 0 ? '+' : ''}${f.delta})` : ''}`) : [];
    return `<div class="gp-brief-watch sev-${sev}"><div class="grow"><div class="title">${esc(w.entity || 'Unnamed entity')}</div>`
      + `<div class="meta">score ${w.score ?? '—'} · ${w.evidenceCount ?? '—'} evidence records${factors.length ? ` · ${esc(factors.join('; '))}` : ''}</div></div>`
      + `<span class="gp-brief-level">${deltaArrow(w.delta)} ${esc(w.level || 'ungraded')}</span></div>`;
  }).join('');

  const method = brief.methodology || {};

  el.innerHTML = `<div class="gp-brief-head"><div class="gp-brief-title">${esc(brief.headline?.title || 'Global Intelligence Brief')}</div>`
    + `<div class="meta">${esc(brief.headline?.description || '')}</div>`
    + `<div class="meta">Snapshot ${esc(formatRelativeTime(freshness.snapshotUpdatedAt))} · events ${esc(formatRelativeTime(freshness.eventsUpdatedAt))} · assessments ${esc(formatRelativeTime(freshness.assessmentsUpdatedAt))}</div></div>`
    + `<h3 class="gp-brief-h">Top developments</h3>`
    + `<div class="gp-filter-row" role="group" aria-label="Filter developments by category">${chips}`
    + `<span class="meta" style="align-self:center;font-size:10px;color:var(--muted-2)">Showing ${shown.length} of ${visible.length} developments</span></div>`
    + (devRows || '<div class="gp-state"><div class="gp-state-title">No developments match</div><div>Nothing in the current brief matches this category.</div></div>')
    + (visible.length > DEV_PAGE ? `<button id="briefMore" class="gp-btn gp-more" type="button">${showAllDevelopments ? 'Show fewer' : `Show all ${visible.length}`}</button>` : '')
    + `<h3 class="gp-brief-h">Watchlist</h3>`
    + (watchRows || '<div class="gp-state"><div class="gp-state-title">Watchlist empty</div><div>No attention indicators in the current brief.</div></div>')
    + (method.caution ? `<div class="gp-brief-caution">${esc(method.caution)}</div>` : '');

  el.querySelectorAll('[data-brief-filter]').forEach(btn => btn.addEventListener('click', () => {
    categoryFilter = btn.dataset.briefFilter; showAllDevelopments = false; renderBriefings();
  }));
  el.querySelector('#briefMore')?.addEventListener('click', () => { showAllDevelopments = !showAllDevelopments; renderBriefings(); });

  const stamp = document.getElementById('briefingsUpdated');
  if (stamp) stamp.textContent = brief.updatedAt ? `Updated ${formatRelativeTime(brief.updatedAt)} · ${developments.length} developments · ${watchlist.length} watched` : '';
}
