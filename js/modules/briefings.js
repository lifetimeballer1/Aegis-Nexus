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

  const judgments = developments.slice(0, 3).map((d, i) =>
    `<div class="gp-brief-watch sev-info"><div class="grow"><div class="title">${i + 1}. ${esc(d.title || 'Untitled development')}</div>`
    + `<div class="meta">${d.reportCount ?? '—'} reports · ${d.independentSourceCount ?? '—'} independent sources · confidence ${esc(d.confidence || 'ungraded')}</div></div></div>`).join('');

  el.innerHTML = `<div class="gp-brief-head"><div class="gp-brief-title">${esc(brief.headline?.title || 'Global Intelligence Brief')}</div>`
    + `<div class="meta">${esc(brief.headline?.description || '')}</div>`
    + `<div class="meta">Snapshot ${esc(formatRelativeTime(freshness.snapshotUpdatedAt))} · events ${esc(formatRelativeTime(freshness.eventsUpdatedAt))} · assessments ${esc(formatRelativeTime(freshness.assessmentsUpdatedAt))}</div></div>`
    + (judgments ? `<h3 class="gp-brief-h">Key Judgments</h3>${judgments}` : '')
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

  renderDrafts(el);
}

/* Analyst Drafts — local-first briefing builder (Concept 05 authoring).
 * Drafts are composed by the analyst from evidence they attach; nothing is
 * generated or fabricated. Stored only in this browser's localStorage;
 * export downloads a JSON file. No backend, no AI generation. */

export const DRAFTS_KEY = 'gp.briefDrafts.v1';
let activeDraftId = null;

function loadDraftStore() {
  try {
    const raw = JSON.parse(localStorage.getItem(DRAFTS_KEY) || '{}');
    if (raw && typeof raw === 'object' && Array.isArray(raw.drafts)) {
      if (typeof raw.activeId === 'string') activeDraftId = raw.activeId;
      return raw;
    }
  } catch {}
  return { drafts: [], activeId: null };
}

function saveDraftStore(store) {
  try { localStorage.setItem(DRAFTS_KEY, JSON.stringify(store)); } catch {}
}

function activeDraft(store) {
  return store.drafts.find(d => d.id === (activeDraftId || store.activeId)) || null;
}

function newDraft() {
  const id = `draft-${Date.now().toString(36)}`;
  return { id, title: 'Untitled briefing', type: 'Situation Update', classification: 'Internal', priority: 'Medium', summary: '', judgments: [], links: [], notes: '', updatedAt: new Date().toISOString() };
}

export function addSupportingToDraft(entry) {
  const store = loadDraftStore();
  let draft = activeDraft(store);
  if (!draft) { draft = newDraft(); store.drafts.push(draft); }
  draft.links.push(entry);
  draft.updatedAt = new Date().toISOString();
  store.activeId = draft.id; activeDraftId = draft.id;
  saveDraftStore(store);
  window.dispatchEvent(new CustomEvent('gp:briefing-drafts-changed'));
}

export function getBriefCategory() { return categoryFilter; }
export function setBriefCategory(c) { categoryFilter = c || 'all'; showAllDevelopments = false; renderBriefings(); }

function draftOptions() {
  return ['Situation Update', 'Regional Brief', 'Thematic Brief'];
}

function renderDrafts(el) {
  const store = loadDraftStore();
  if (!activeDraftId) activeDraftId = store.activeId || null;
  let draft = activeDraft(store);
  if (!draft && store.drafts.length) { draft = store.drafts[0]; activeDraftId = draft.id; }

  const listBtns = store.drafts.map(d =>
    `<button class="gp-filter${draft && d.id === draft.id ? ' active' : ''}" data-draft-sel="${esc(d.id)}" type="button">${esc(d.title || 'Untitled briefing')}</button>`).join('');

  const editor = draft ? `
    <div class="gp-dash-panel" style="margin-top:8px"><h3>Content</h3>
      <label style="font-size:10px;color:var(--muted-2)">Title<input id="bdTitle" class="gp-map-search" type="text" value="${esc(draft.title)}" maxlength="120"></label>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">
        <label style="font-size:10px;color:var(--muted-2)">Type <select id="bdType" class="gp-map-search">${draftOptions().map(o => `<option${o === draft.type ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select></label>
        <label style="font-size:10px;color:var(--muted-2)">Classification <select id="bdClass" class="gp-map-search">${['Internal', 'Unclassified'].map(o => `<option${o === draft.classification ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select></label>
        <label style="font-size:10px;color:var(--muted-2)">Priority <select id="bdPri" class="gp-map-search">${['Low', 'Medium', 'High', 'Critical'].map(o => `<option${o === draft.priority ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select></label>
      </div>
      <label style="font-size:10px;color:var(--muted-2);margin-top:6px;display:block">Executive summary<textarea id="bdSummary" class="gp-map-search" rows="3" maxlength="2000" style="width:100%;resize:vertical">${esc(draft.summary)}</textarea></label>
    </div>
    <div class="gp-dash-panel" style="margin-top:8px"><h3>Key judgments</h3>
      <div class="gp-dash-list">${(draft.judgments || []).map((j, i) => `<div class="gp-dash-row"><div class="grow"><div class="title">${i + 1}. ${esc(j.text || '')}</div></div><button class="gp-btn" data-jdel="${i}" type="button">Remove</button></div>`).join('') || '<div class="meta">No judgments yet — add the analyst’s own assessments.</div>'}</div>
      <div style="display:flex;gap:6px;margin-top:6px"><input id="bdJudgNew" class="gp-map-search" type="text" placeholder="New judgment…" maxlength="280" style="flex:1"><button class="gp-btn" data-jadd type="button">Add</button></div>
    </div>
    <div class="gp-dash-panel" style="margin-top:8px"><h3>Supporting content</h3>
      <div class="meta" style="font-size:10px;color:var(--muted-2);margin-bottom:6px">Attach evidence only — alerts via “Add to briefing”, or paste source URLs.</div>
      <div class="gp-dash-list">${(draft.links || []).map((l, i) => `<div class="gp-dash-row"><div class="grow"><div class="title">${esc(l.label || l.key || 'link')}</div><div class="meta">${esc(l.kind === 'alert' ? `alert · ${l.key || ''}` : l.url || '')}</div></div><button class="gp-btn" data-ldel="${i}" type="button">Remove</button></div>`).join('') || '<div class="meta">Nothing attached yet.</div>'}</div>
      <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap"><input id="bdLinkLabel" class="gp-map-search" type="text" placeholder="Label" maxlength="120" style="flex:1;min-width:120px"><input id="bdLinkUrl" class="gp-map-search" type="url" placeholder="https://…" maxlength="500" style="flex:2;min-width:160px"><button class="gp-btn" data-ladd type="button">Attach URL</button></div>
    </div>
    <div class="gp-dash-panel" style="margin-top:8px"><h3>Analyst notes</h3>
      <textarea id="bdNotes" class="gp-map-search" rows="2" maxlength="2000" style="width:100%;resize:vertical" placeholder="Private working notes — stored on this device only.">${esc(draft.notes)}</textarea>
      <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap"><button class="gp-btn" data-bdexport type="button">Export JSON</button><button class="gp-btn" data-draft-del type="button">Delete draft</button><span class="meta" id="bdSaved" style="align-self:center">${draft.updatedAt ? `Saved ${esc(formatRelativeTime(draft.updatedAt))}` : ''}</span></div>
    </div>`
    : '<div class="gp-state"><div class="gp-state-title">No drafts yet</div><div>Start a briefing draft to collect judgments and evidence.</div></div>';

  const host = document.createElement('div');
  host.innerHTML = `<h3 class="gp-brief-h" style="margin-top:12px">Analyst drafts <span style="font-weight:400;color:var(--muted);font-size:10px">stored on this device only</span></h3>`
    + `<div class="gp-filter-row" role="group" aria-label="Briefing drafts">${listBtns}<button class="gp-btn" data-draft-new type="button">+ New draft</button></div>`
    + editor;
  el.appendChild(host);

  const touch = () => {
    const s = loadDraftStore();
    const d = activeDraft(s);
    if (!d) return;
    d.updatedAt = new Date().toISOString();
    saveDraftStore(s);
    const stampEl = document.getElementById('bdSaved');
    if (stampEl) stampEl.textContent = 'Saved just now';
  };
  const mutate = (fn) => {
    const s = loadDraftStore();
    const d = activeDraft(s);
    if (!d) return;
    fn(d, s);
    d.updatedAt = new Date().toISOString();
    saveDraftStore(s);
    renderBriefings();
  };
  host.querySelector('[data-draft-new]')?.addEventListener('click', () => {
    const s = loadDraftStore();
    const d = newDraft();
    s.drafts.push(d); s.activeId = d.id; activeDraftId = d.id;
    saveDraftStore(s); renderBriefings();
  });
  host.querySelectorAll('[data-draft-sel]').forEach(b => b.addEventListener('click', () => {
    activeDraftId = b.dataset.draftSel;
    const s = loadDraftStore(); s.activeId = activeDraftId; saveDraftStore(s);
    renderBriefings();
  }));
  host.querySelector('[data-draft-del]')?.addEventListener('click', () => {
    mutate((d, s) => { s.drafts = s.drafts.filter(x => x.id !== d.id); activeDraftId = null; s.activeId = null; });
  });
  const bindField = (id, key) => host.querySelector(`#${id}`)?.addEventListener('input', (e) => {
    const s = loadDraftStore();
    const d = activeDraft(s);
    if (!d) return;
    d[key] = e.target.value;
    saveDraftStore(s);
    const stampEl = document.getElementById('bdSaved');
    if (stampEl) stampEl.textContent = 'Editing…';
    clearTimeout(bindField._t);
    bindField._t = setTimeout(touch, 800);
  });
  ['bdTitle', 'bdType', 'bdClass', 'bdPri', 'bdSummary', 'bdNotes'].forEach((id, i) =>
    bindField(id, ['title', 'type', 'classification', 'priority', 'summary', 'notes'][i]));
  host.querySelector('[data-jadd]')?.addEventListener('click', () => {
    const v = (host.querySelector('#bdJudgNew')?.value || '').trim();
    if (!v) return;
    mutate((d) => { d.judgments.push({ text: v }); });
  });
  host.querySelectorAll('[data-jdel]').forEach(b => b.addEventListener('click', () => {
    const i = Number(b.dataset.jdel);
    mutate((d) => { d.judgments.splice(i, 1); });
  }));
  host.querySelector('[data-ladd]')?.addEventListener('click', () => {
    const label = (host.querySelector('#bdLinkLabel')?.value || '').trim();
    const url = (host.querySelector('#bdLinkUrl')?.value || '').trim();
    if (!/^https?:\/\//i.test(url)) {
      const stampEl = document.getElementById('bdSaved');
      if (stampEl) stampEl.textContent = 'URL must start with http(s)://';
      return;
    }
    mutate((d) => { d.links.push({ kind: 'url', label: label || url, url }); });
  });
  host.querySelectorAll('[data-ldel]').forEach(b => b.addEventListener('click', () => {
    const i = Number(b.dataset.ldel);
    mutate((d) => { d.links.splice(i, 1); });
  }));
  host.querySelector('[data-bdexport]')?.addEventListener('click', () => {
    const s = loadDraftStore();
    const d = activeDraft(s);
    if (!d) return;
    const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `briefing-${d.id}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  });
}
