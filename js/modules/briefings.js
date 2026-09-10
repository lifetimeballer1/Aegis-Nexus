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

  const chips = [`<button class="gp-filter${categoryFilter === 'all' ? ' active' : ''}" data-brief-filter="all" type="button" aria-pressed="${categoryFilter === 'all'}">All (${developments.length})</button>`]
    .concat(categories.map(c => `<button class="gp-filter${categoryFilter === c ? ' active' : ''}" data-brief-filter="${esc(c)}" type="button" aria-pressed="${categoryFilter === c}">${esc(c)} (${developments.filter(d => String(d.category || 'general') === c).length})</button>`)).join('');

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

  const pins = loadPins();
  const watchRows = watchlist.slice(0, 10).map(w => {
    const sev = watchSeverity(w.level);
    const pinned = pins.includes(w.entity);
    const factors = Array.isArray(w.topFactors) ? w.topFactors.slice(0, 3).map(f => `${f.label || ''}${f.delta !== undefined && f.delta !== null ? ` (${Number(f.delta) > 0 ? '+' : ''}${f.delta})` : ''}`) : [];
    return `<div class="gp-brief-watch sev-${sev}"><div class="grow"><div class="title">${esc(w.entity || 'Unnamed entity')}</div>`
      + `<div class="meta">score ${w.score ?? '—'} · ${w.evidenceCount ?? '—'} evidence records${factors.length ? ` · ${esc(factors.join('; '))}` : ''}</div></div>`
      + `<span class="gp-brief-level">${deltaArrow(w.delta)} ${esc(w.level || 'ungraded')}</span>`
      + (w.entity ? `<button class="gp-btn" data-watch-pin="${esc(w.entity)}" type="button" title="Pin to My Watchlist on this device">${pinned ? 'Pinned ✓' : 'Pin'}</button>` : '') + `</div>`;
  }).join('');
  const myRows = pins.map(name => {
    const live = watchlist.find(w => w.entity === name);
    return `<div class="gp-dash-row"><div class="grow"><div class="title" style="font-size:11px">${esc(name)}</div>`
      + `<div class="meta">${live ? `level ${esc(live.level || 'ungraded')} · score ${live.score ?? '—'} · ${live.evidenceCount ?? '—'} evidence records` : 'not in the current brief'}</div></div>`
      + `<button class="gp-btn" data-watch-unpin="${esc(name)}" type="button">Unpin</button></div>`;
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
    + `<div class="gp-dash-panel" style="margin-top:8px"><h3>My Watchlist <span style="font-weight:400;color:var(--muted);font-size:10px">${pins.length} pinned · this device only</span></h3>`
    + (myRows ? `<div class="gp-dash-list">${myRows}</div><div style="margin-top:8px"><button class="gp-btn" data-watch-export type="button">Export watchlist JSON</button></div>` : '<div class="meta">Nothing pinned yet — pin entities from the pipeline watchlist above.</div>') + `</div>`
    + (method.caution ? `<div class="gp-brief-caution">${esc(method.caution)}</div>` : '');

  el.querySelectorAll('[data-brief-filter]').forEach(btn => btn.addEventListener('click', () => {
    categoryFilter = btn.dataset.briefFilter; showAllDevelopments = false; renderBriefings();
  }));
  el.querySelector('#briefMore')?.addEventListener('click', () => { showAllDevelopments = !showAllDevelopments; renderBriefings(); });
  el.querySelectorAll('[data-watch-pin]').forEach(btn => btn.addEventListener('click', () => {
    const name = btn.dataset.watchPin;
    const list = loadPins();
    if (list.includes(name)) savePins(list.filter(x => x !== name));
    else { list.push(name); savePins(list); }
    renderBriefings();
  }));
  el.querySelectorAll('[data-watch-unpin]').forEach(btn => btn.addEventListener('click', () => {
    savePins(loadPins().filter(x => x !== btn.dataset.watchUnpin));
    renderBriefings();
  }));
  el.querySelector('[data-watch-export]')?.addEventListener('click', () => {
    const brief = getState().intelligenceBrief || {};
    const live = Array.isArray(brief.watchlist) ? brief.watchlist : [];
    const payload = { exportedAt: new Date().toISOString(), pins: loadPins().map(name => ({ entity: name, live: live.find(w => w.entity === name) || null })) };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'my-watchlist.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  });

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
let draftStep = 1;

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

function downloadFile(name, content, type) {
  const blob = new Blob([content], { type });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
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

/* My Watchlist — analyst-pinned entities (device-local). Live level/score
 * resolve against the current pipeline brief watchlist by entity name;
 * pins absent from the current brief say so honestly. */
const MYWATCH_KEY = 'gp.mywatch.v1';
function loadPins() {
  try {
    const raw = JSON.parse(localStorage.getItem(MYWATCH_KEY) || '[]');
    return Array.isArray(raw) ? raw.filter(x => typeof x === 'string') : [];
  } catch { return []; }
}
function savePins(pins) {
  try { localStorage.setItem(MYWATCH_KEY, JSON.stringify(pins)); } catch {}
}

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

  const stepsNav = `<div class="gp-steps" role="tablist" aria-label="Briefing builder steps">`
    + [['1', 'Content'], ['2', 'Structure'], ['3', 'Review'], ['4', 'Publish']].map(([n, label], i) =>
      `${i ? '<span class="gp-step-line" aria-hidden="true"></span>' : ''}<button class="gp-step${draftStep === i + 1 ? ' active' : ''}${draftStep > i + 1 ? ' done' : ''}" data-draft-step="${i + 1}" type="button" role="tab" aria-selected="${draftStep === i + 1}"><span class="gp-step-num">${draftStep > i + 1 ? '✓' : n}</span>${label}</button>`).join('')
    + `</div>`;
  const judgments = Array.isArray(draft?.judgments) ? draft.judgments : [];
  const links = Array.isArray(draft?.links) ? draft.links : [];
  const missing = [];
  if (!draft || !String(draft.title || '').trim() || draft.title === 'Untitled briefing') missing.push('a title');
  if (!draft || !String(draft.summary || '').trim()) missing.push('an executive summary');
  if (!judgments.length) missing.push('at least one key judgment');

  const editor = draft ? `
    ${stepsNav}
    <div class="gp-step-panel${draftStep === 1 ? ' active' : ''}" data-draft-panel="1">
      <div class="gp-panel" style="margin-top:10px"><div class="gp-panel-head"><h4 class="gp-panel-title">1 · Content</h4><span class="gp-tiny gp-muted">Analyst-authored · device-local</span></div>
      <div class="gp-panel-body gp-stack">
        <div class="gp-field"><label for="bdTitle">Title</label><input id="bdTitle" class="gp-input" type="text" value="${esc(draft.title)}" maxlength="120"><span class="gp-counter" data-counter-for="bdTitle">${String(draft.title || '').length}/120</span></div>
        <div class="gp-grid gp-grid-3">
          <div class="gp-field"><label for="bdType">Briefing type</label><select id="bdType" class="gp-select">${draftOptions().map(o => `<option${o === draft.type ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select></div>
          <div class="gp-field"><label for="bdClass">Classification</label><select id="bdClass" class="gp-select">${['Internal', 'Unclassified'].map(o => `<option${o === draft.classification ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select></div>
          <div class="gp-field"><label for="bdPri">Priority</label><select id="bdPri" class="gp-select">${['Low', 'Medium', 'High', 'Critical'].map(o => `<option${o === draft.priority ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select></div>
        </div>
        <div class="gp-field"><label for="bdSummary">Executive summary</label><textarea id="bdSummary" class="gp-textarea" rows="5" maxlength="2000">${esc(draft.summary)}</textarea><span class="gp-counter" data-counter-for="bdSummary">${String(draft.summary || '').length}/2000</span></div>
      </div></div>
      <div class="gp-row" style="justify-content:flex-end;margin-top:8px"><button class="gp-btn primary" data-draft-next type="button">Next: Structure →</button></div>
    </div>
    <div class="gp-step-panel${draftStep === 2 ? ' active' : ''}" data-draft-panel="2">
      <div class="gp-panel" style="margin-top:10px"><div class="gp-panel-head"><h4 class="gp-panel-title">2 · Structure</h4></div>
      <div class="gp-panel-body gp-stack">
        <div><div class="gp-tiny gp-muted" style="margin-bottom:6px;text-transform:uppercase;letter-spacing:.08em">Key judgments</div>
          <div class="gp-stack">${judgments.map((j, i) => `<div class="gp-row-between" style="border:1px solid var(--line);border-radius:var(--radius);padding:8px 10px"><span style="font-size:12px;min-width:0">${i + 1}. ${esc(j.text || '')}</span><span class="gp-row"><button class="gp-btn" data-jup="${i}" type="button" ${i === 0 ? 'disabled' : ''} aria-label="Move judgment up">↑</button><button class="gp-btn" data-jdown="${i}" type="button" ${i === judgments.length - 1 ? 'disabled' : ''} aria-label="Move judgment down">↓</button><button class="gp-btn" data-jdel="${i}" type="button">Remove</button></span></div>`).join('') || '<div class="gp-muted gp-tiny">No judgments yet — add the analyst’s own assessments.</div>'}</div>
          <div class="gp-row" style="margin-top:6px"><input id="bdJudgNew" class="gp-input" type="text" placeholder="New judgment…" maxlength="280" style="flex:1"><button class="gp-btn" data-jadd type="button">Add</button></div></div>
        <div><div class="gp-tiny gp-muted" style="margin:10px 0 6px;text-transform:uppercase;letter-spacing:.08em">Supporting content</div>
          <div class="gp-stack">${links.map((l, i) => `<div class="gp-row-between" style="border:1px solid var(--line);border-radius:var(--radius);padding:8px 10px"><span style="min-width:0"><span style="font-size:12px">${esc(l.label || l.key || 'link')}</span><span class="gp-tiny gp-muted" style="display:block">${esc(l.kind === 'alert' ? `alert · ${l.key || ''}` : l.url || '')}</span></span><button class="gp-btn" data-ldel="${i}" type="button">Remove</button></div>`).join('') || '<div class="gp-muted gp-tiny">Nothing attached yet — attach evidence via “Add to briefing” on an alert, or paste a source URL below.</div>'}</div>
          <div class="gp-row" style="margin-top:6px"><input id="bdLinkLabel" class="gp-input" type="text" placeholder="Label" maxlength="120" style="flex:1;min-width:120px"><input id="bdLinkUrl" class="gp-input" type="url" placeholder="https://…" maxlength="500" style="flex:2;min-width:160px"><button class="gp-btn" data-ladd type="button">Attach URL</button></div></div>
        <div class="gp-field"><label for="bdNotes">Analyst notes</label><textarea id="bdNotes" class="gp-textarea" rows="2" maxlength="2000" placeholder="Private working notes — stored on this device only.">${esc(draft.notes)}</textarea></div>
      </div></div>
      <div class="gp-row-between" style="margin-top:8px"><button class="gp-btn" data-draft-prev type="button">← Back</button><button class="gp-btn primary" data-draft-next type="button">Next: Review →</button></div>
    </div>
    <div class="gp-step-panel${draftStep === 3 ? ' active' : ''}" data-draft-panel="3">
      <div class="gp-panel" style="margin-top:10px"><div class="gp-panel-head"><h4 class="gp-panel-title">3 · Review</h4></div>
      <div class="gp-panel-body">
        ${missing.length ? `<div class="gp-honest" style="margin-bottom:10px">Before publishing, add ${esc(missing.join(', '))}. Drafts are never auto-completed.</div>` : '<div class="gp-row" style="margin-bottom:10px"><span class="gp-sev sev-low">Ready</span><span class="gp-tiny gp-muted">Required fields present</span></div>'}
        <div class="gp-brief-head"><div class="gp-brief-title">${esc(draft.title || 'Untitled briefing')}</div><div class="meta">${esc(draft.type || '')} · ${esc(draft.classification || '')} · priority ${esc(draft.priority || '')}</div></div>
        <h3 class="gp-brief-h">Executive summary</h3><p style="font-size:12.5px;line-height:1.55;color:var(--text-secondary)">${esc(draft.summary || '—')}</p>
        <h3 class="gp-brief-h">Key judgments</h3>${judgments.map((j, i) => `<div class="gp-brief-watch sev-info"><div class="grow"><div class="title">${i + 1}. ${esc(j.text || '')}</div></div></div>`).join('') || '<div class="gp-muted gp-tiny">None yet.</div>'}
        <h3 class="gp-brief-h">Supporting content</h3>${links.map(l => `<div class="gp-tiny gp-muted">• ${esc(l.label || l.key || '')}${l.url ? ` — ${esc(l.url)}` : ''}</div>`).join('') || '<div class="gp-muted gp-tiny">None yet.</div>'}
      </div></div>
      <div class="gp-row-between" style="margin-top:8px"><button class="gp-btn" data-draft-prev type="button">← Back</button><button class="gp-btn primary" data-draft-next type="button">Next: Publish →</button></div>
    </div>
    <div class="gp-step-panel${draftStep === 4 ? ' active' : ''}" data-draft-panel="4">
      <div class="gp-panel" style="margin-top:10px"><div class="gp-panel-head"><h4 class="gp-panel-title">4 · Publish</h4><span class="gp-tiny gp-muted">Local export only</span></div>
      <div class="gp-panel-body gp-stack">
        <div class="gp-honest">This build has no delivery backend. Publishing exports a local file (JSON / Markdown) or opens the browser print dialog. No email, chat, SMS, or generated content is available or simulated.</div>
        <div class="gp-row"><button class="gp-btn primary" data-bdexport type="button">Export JSON</button><button class="gp-btn" data-bdmarkdown type="button">Export Markdown</button><button class="gp-btn" data-bdprint type="button">Print preview</button></div>
        <div class="gp-row-between"><span class="meta" id="bdSaved">${draft.updatedAt ? `Saved ${esc(formatRelativeTime(draft.updatedAt))}` : ''}</span><button class="gp-btn" data-draft-del type="button">Delete draft</button></div>
      </div></div>
      <div class="gp-row" style="margin-top:8px"><button class="gp-btn" data-draft-prev type="button">← Back</button></div>
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
    s.drafts.push(d); s.activeId = d.id; activeDraftId = d.id; draftStep = 1;
    saveDraftStore(s); renderBriefings();
  });
  host.querySelectorAll('[data-draft-sel]').forEach(b => b.addEventListener('click', () => {
    activeDraftId = b.dataset.draftSel; draftStep = 1;
    const s = loadDraftStore(); s.activeId = activeDraftId; saveDraftStore(s);
    renderBriefings();
  }));
  host.querySelectorAll('[data-draft-step]').forEach(b => b.addEventListener('click', () => {
    draftStep = Number(b.dataset.draftStep) || 1; renderBriefings();
  }));
  host.querySelectorAll('[data-draft-next]').forEach(b => b.addEventListener('click', () => {
    draftStep = Math.min(4, draftStep + 1); renderBriefings();
  }));
  host.querySelectorAll('[data-draft-prev]').forEach(b => b.addEventListener('click', () => {
    draftStep = Math.max(1, draftStep - 1); renderBriefings();
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
    const counter = host.querySelector(`[data-counter-for="${id}"]`);
    if (counter) counter.textContent = `${e.target.value.length}/${e.target.maxLength > 0 ? e.target.maxLength : ''}`;
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
  host.querySelectorAll('[data-jup]').forEach(b => b.addEventListener('click', () => {
    const i = Number(b.dataset.jup);
    mutate((d) => { if (i > 0) { const t = d.judgments[i - 1]; d.judgments[i - 1] = d.judgments[i]; d.judgments[i] = t; } });
  }));
  host.querySelectorAll('[data-jdown]').forEach(b => b.addEventListener('click', () => {
    const i = Number(b.dataset.jdown);
    mutate((d) => { if (i < d.judgments.length - 1) { const t = d.judgments[i + 1]; d.judgments[i + 1] = d.judgments[i]; d.judgments[i] = t; } });
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
    downloadFile(`briefing-${d.id}.json`, JSON.stringify(d, null, 2), 'application/json');
  });
  host.querySelector('[data-bdmarkdown]')?.addEventListener('click', () => {
    const s = loadDraftStore();
    const d = activeDraft(s);
    if (!d) return;
    const md = [
      `# ${d.title || 'Untitled briefing'}`, '',
      `*${d.type || ''} · ${d.classification || ''} · Priority: ${d.priority || ''}*`, '',
      '## Executive summary', '', d.summary || '', '',
      '## Key judgments', '', ...(d.judgments || []).map((j, i) => `${i + 1}. ${j.text || ''}`), '',
      '## Supporting content', '', ...(d.links || []).map(l => `- ${l.label || l.key || 'link'}${l.url ? ` — ${l.url}` : ''}`), '',
      '## Analyst notes', '', d.notes || '', ''
    ].join('\n');
    downloadFile(`briefing-${d.id}.md`, md, 'text/markdown');
  });
  host.querySelector('[data-bdprint]')?.addEventListener('click', () => {
    const s = loadDraftStore();
    const d = activeDraft(s);
    if (!d) return;
    const w = window.open('', '_blank');
    if (!w) {
      const stampEl = document.getElementById('bdSaved');
      if (stampEl) stampEl.textContent = 'Print preview blocked by the browser.';
      return;
    }
    const judgments = (d.judgments || []).map((j, i) => `<li>${esc(j.text || '')}</li>`).join('');
    const links = (d.links || []).map(l => `<li>${esc(l.label || l.key || 'link')}${l.url ? ` — ${esc(l.url)}` : ''}</li>`).join('');
    w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${esc(d.title || 'Briefing')}</title><style>body{font-family:system-ui,-apple-system,sans-serif;max-width:720px;margin:32px auto;padding:0 16px;color:#111;line-height:1.5}h1{font-size:20px}h2{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-top:20px}ul{margin:6px 0 0 18px}</style></head><body><h1>${esc(d.title || 'Untitled briefing')}</h1><p><em>${esc(d.type || '')} · ${esc(d.classification || '')} · Priority: ${esc(d.priority || '')}</em></p><h2>Executive summary</h2><p>${esc(d.summary || '—')}</p><h2>Key judgments</h2><ul>${judgments || '<li>None yet.</li>'}</ul><h2>Supporting content</h2><ul>${links || '<li>None yet.</li>'}</ul><h2>Analyst notes</h2><p>${esc(d.notes || '—')}</p></body></html>`);
    w.document.close();
    w.focus();
    w.print();
  });
}
