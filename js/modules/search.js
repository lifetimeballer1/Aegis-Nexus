/** GUI Phase 8 — Universal Search workspace.
 * One query across the already-wired canonical state: stories, conflicts,
 * events, Brain nodes, Web graph entities, map signals, and brief records.
 * Results are grouped by domain with real match counts and deep-link to
 * their home sections; Brain/Web node hits additionally dispatch
 * gp:brain-select so those workspaces refocus (their listeners ignore
 * same-source events). Nothing is fabricated: unscanned or unloaded
 * domains report so honestly. Severity follows the shared language. */
import { getState } from '../core/state.js';
import { escapeHtml } from '../core/utils.js';

let universalQuery = '';

const GROUP_CAP = 4;
const MIN_QUERY = 2;

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

function textOf(item, keys) {
  return keys.map(k => item?.[k]).filter(v => v !== undefined && v !== null).join(' ');
}

function matchScore(haystack, q) {
  const hay = String(haystack || '').toLowerCase();
  if (!q || !hay.includes(q)) return -1;
  return hay.indexOf(q);
}

function collectGroup(items, query, toResult) {
  const out = [];
  for (const item of (items || [])) {
    if (!item || typeof item !== 'object') continue;
    const result = toResult(item);
    if (!result) continue;
    if (matchScore(`${result.title} ${result.meta}`, query) < 0) continue;
    out.push(result);
  }
  return out;
}

function collectGroups(state, query) {
  const groups = [];
  const live = state.liveArticles;
  const stories = Array.isArray(live) ? live : (live?.articles || state.snapshot?.stories || []);
  groups.push({
    key: 'stories', label: 'Stories', section: '#section-breaking',
    items: collectGroup(stories, query, s => {
      const title = s.title || s.headline;
      if (!title) return null;
      const url = s.url || s.link || '';
      return { title, meta: `${s.sourceLabel || s.sourceName || s.source || ''}`, href: /^https?:\/\//i.test(url) ? url : null, external: true };
    })
  });
  const conflicts = Array.isArray(state.snapshot?.conflicts) ? state.snapshot.conflicts : [];
  groups.push({
    key: 'conflicts', label: 'Conflicts', section: '#section-conflicts',
    items: collectGroup(conflicts, query, c => {
      const title = c.name || c.id;
      if (!title) return null;
      return { title, meta: [c.region, c.escalation ? `escalation ${c.escalation}` : ''].filter(Boolean).join(' · ') };
    })
  });
  const events = Array.isArray(state.mapData?.events?.events) ? state.mapData.events.events : [];
  groups.push({
    key: 'events', label: 'Events', section: '#section-alerts',
    items: collectGroup(events, query, e => {
      if (!e.title) return null;
      return { title: e.title, meta: [e.category, e.confidence ? `confidence ${e.confidence}` : ''].filter(Boolean).join(' · ') };
    })
  });
  const brain = state.intelligenceBrain || state.snapshot?.intelligenceBrain || {};
  const brainNodes = Array.isArray(brain.nodes) ? brain.nodes : [];
  groups.push({
    key: 'brain', label: 'Brain', section: '#section-brain',
    items: collectGroup(brainNodes, query, n => {
      const id = n.id !== undefined && n.id !== null ? String(n.id) : '';
      const title = n.label || n.name || id;
      if (!title) return null;
      return { title, meta: String(n.kind || n.type || 'entity'), brainId: id || null };
    })
  });
  const graph = state.intelligenceGraph || {};
  const graphNodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  groups.push({
    key: 'web', label: 'Web', section: '#section-intelweb',
    items: collectGroup(graphNodes, query, n => {
      const id = n.id !== undefined && n.id !== null ? String(n.id) : '';
      const title = n.label || n.name || id;
      if (!title) return null;
      return { title, meta: String(n.kind || n.type || 'entity'), brainId: id || null };
    })
  });
  const markers = Array.isArray(state.mapPoints?.markers) ? state.mapPoints.markers : [];
  groups.push({
    key: 'map', label: 'Map', section: '#section-map',
    items: collectGroup(markers, query, m => {
      const title = m.title || m.label || m.name || m.location;
      if (!title || m.lat === undefined || m.lng === undefined) return null;
      return { title, meta: [m.source, m.eventType].filter(Boolean).join(' · ') };
    })
  });
  const brief = state.intelligenceBrief || {};
  const devs = Array.isArray(brief.topDevelopments) ? brief.topDevelopments : [];
  const watch = Array.isArray(brief.watchlist) ? brief.watchlist : [];
  groups.push({
    key: 'brief', label: 'Brief', section: '#section-briefings',
    items: [
      ...collectGroup(devs, query, d => d.title ? { title: d.title, meta: String(d.category || 'development') } : null),
      ...collectGroup(watch, query, w => w.entity ? { title: w.entity, meta: `watchlist · ${w.level || 'ungraded'}` } : null)
    ]
  });
  return groups;
}

export function renderSearch() {
  const el = document.getElementById('searchBody');
  if (!el) return;
  const state = getState();
  const q = universalQuery.trim().toLowerCase();

  const indexed = (Array.isArray(state.liveArticles) ? state.liveArticles.length : (state.liveArticles?.articles?.length || 0))
    + (state.snapshot?.conflicts?.length || 0)
    + (state.mapData?.events?.events?.length || 0)
    + ((state.intelligenceBrain || state.snapshot?.intelligenceBrain)?.nodes?.length || 0)
    + (state.intelligenceGraph?.nodes?.length || 0)
    + (state.mapPoints?.markers?.length || 0)
    + (state.intelligenceBrief?.topDevelopments?.length || 0)
    + (state.intelligenceBrief?.watchlist?.length || 0);
  const stamp = document.getElementById('searchUpdated');
  if (stamp) stamp.textContent = indexed ? `${indexed.toLocaleString()} records indexed` : '';

  if (!state.snapshot && !state.liveArticles && !state.intelligenceGraph && !state.mapPoints && !state.intelligenceBrief) {
    el.innerHTML = state.status === 'loading'
      ? '<div class="gp-state"><div class="gp-spinner"></div><div>Loading search index…</div></div>'
      : '<div class="gp-state"><div class="gp-state-title">Search unavailable</div><div>Core data failed to load, so there is nothing to search.</div></div>';
    return;
  }

  if (q.length < MIN_QUERY) {
    el.innerHTML = `<input id="universalSearch" class="gp-map-search" type="search" aria-label="Search all intelligence" placeholder="Search stories, conflicts, Brain, map, brief…" value="${esc(universalQuery)}">`
      + '<div class="gp-state"><div class="gp-state-title">Search everything</div><div>Type at least 2 characters to search stories, conflicts, events, Brain nodes, Web entities, map signals, and brief records.</div><div class="meta" style="margin-top:6px">Tip: press Ctrl+K (or /) from anywhere to jump here.</div></div>';
  } else {
    const groups = collectGroups(state, q);
    const total = groups.reduce((n, g) => n + g.items.length, 0);
    const blocks = groups.map(g => {
      if (!g.items.length) return '';
      const rows = g.items.slice(0, GROUP_CAP).map(r => {
        const link = r.external && r.href
          ? `<a href="${esc(r.href)}" target="_blank" rel="noopener noreferrer">${esc(r.title)}</a>`
          : `<a href="${esc(g.section)}"${r.brainId ? ` data-search-brain="${esc(r.brainId)}" data-search-section="${esc(g.section)}"` : ''}>${esc(r.title)}</a>`;
        return `<div class="gp-search-row"><div class="grow"><div class="title">${link}</div>`
          + (r.meta ? `<div class="meta">${esc(r.meta)}</div>` : '') + '</div></div>';
      }).join('');
      return `<div class="gp-search-group"><h3 class="gp-brief-h">${esc(g.label)} <span class="meta">(${g.items.length})</span> <a href="${esc(g.section)}">Open →</a></h3>`
        + rows
        + (g.items.length > GROUP_CAP ? `<div class="meta"><a href="${esc(g.section)}">See all ${g.items.length} in ${esc(g.label)} →</a></div>` : '') + '</div>';
    }).join('');
    el.innerHTML = `<input id="universalSearch" class="gp-map-search" type="search" aria-label="Search all intelligence" placeholder="Search stories, conflicts, Brain, map, brief…" value="${esc(universalQuery)}">`
      + `<div class="meta" style="font-size:10px;color:var(--muted-2);margin:6px 0">Showing up to ${GROUP_CAP} per domain · ${total} total matches</div>`
      + (blocks || '<div class="gp-state"><div class="gp-state-title">No results match</div><div>Nothing in the loaded artifacts matches this query.</div></div>');
  }

  const input = el.querySelector('#universalSearch');
  input?.addEventListener('input', () => {
    universalQuery = input.value;
    renderSearch();
    const again = document.getElementById('universalSearch');
    if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); }
  });
  el.querySelectorAll('[data-search-brain]').forEach(a => a.addEventListener('click', () => {
    const id = a.dataset.searchBrain;
    if (!id) return;
    window.dispatchEvent(new CustomEvent('gp:brain-select', { detail: { id, source: 'search' } }));
  }));
}
