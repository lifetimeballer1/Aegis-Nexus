/** Intelligence Brain — cross-domain view of the canonical brain artifact. */
import { getState } from '../core/state.js';
import { escapeHtml, formatRelativeTime } from '../core/utils.js';

let selectedId = null;
let query = '';
let kindFilter = 'all';
let relationshipFilter = 'all';
let showAll = false;
let showAllEvidence = false;
let showAllRelationships = false;
let selectedStoryId = null;
let showAllStories = false;

function storyGaps(story, gaps) {
  return gaps.filter(g => String(g.storyId) === String(story.id) && g.state !== 'closed');
}

function storyMatches(story, q) {
  if (!q) return true;
  const hay = [story.title, story.hub, story.kind, story.region, (story.actors || []).join(' '), (story.targets || []).join(' ')].join(' ').toLowerCase();
  return hay.includes(q);
}

function severityChip(sev) {
  if (sev === 'critical') return 'gp-sev-critical';
  if (sev === 'high') return 'gp-sev-high';
  if (sev === 'medium') return 'gp-sev-medium';
  return 'gp-sev-low';
}

function deltaStripHtml(lastCycle) {
  if (!lastCycle) return '';
  return `<span class="gp-brain-chip">${Number(lastCycle.stories || 0)} stories</span>`
    + `<span class="gp-brain-chip">${Number(lastCycle.open || 0)} open gaps</span>`
    + `<span class="gp-brain-chip">+${(lastCycle.opened || []).length} opened</span>`
    + `<span class="gp-brain-chip">✓ ${(lastCycle.closedNow || []).length} filled</span>`
    + `<span class="gp-brain-chip">${Number(lastCycle.narrowing || 0)} narrowing</span>`;
}

function storyCardHtml(story, gaps, selected) {
  const open = storyGaps(story, gaps);
  const gapLabel = open.length ? `${open.length} gap${open.length === 1 ? '' : 's'}` : 'no open gaps';
  return `<div class="gp-card gp-story-card sev-${escapeHtml(story.severity || 'low')}${selected ? ' selected' : ''}">
    <button class="gp-story-head" data-story="${escapeHtml(String(story.id))}" type="button" aria-expanded="${selected}">
      <span class="gp-story-title">${escapeHtml(story.title || 'Untitled story')}</span>
      <span class="gp-card-meta" style="margin-top:4px"><span class="gp-sev ${severityChip(story.severity)}">${escapeHtml(story.severity || 'low')}</span>${story.hub ? `<span>${escapeHtml(story.hub)}</span>` : ''}<span>${escapeHtml(story.confidence || 'unverified')}</span><span>${escapeHtml(gapLabel)}</span><span>pressure ${escapeHtml(String(story.tensionContribution ?? 0))}</span></span>
      <span class="gp-completeness" title="Completeness ${Math.round((story.completeness || 0) * 100)}%"><i style="width:${Math.round((story.completeness || 0) * 100)}%"></i></span>
    </button>
  </div>`;
}

function storyDetailHtml(story, gaps, evidenceLimit) {
  const open = storyGaps(story, gaps);
  const ev = evidenceItems(story);
  const actorChips = (story.actors || []).map(a => `<span class="gp-brain-chip">${escapeHtml(a)}</span>`).join('');
  const targetChips = (story.targets || []).map(a => `<span class="gp-brain-chip">${escapeHtml(a)}</span>`).join('');
  const gapRows = open.map(g => `<div class="gp-gap-row sev-${escapeHtml(g.severity || 'low')}"><span class="gp-sev ${severityChip(g.severity)}">${escapeHtml(g.type)}</span><span class="grow">${escapeHtml(g.evidenceNeeded || '')}</span><span class="gp-tiny gp-muted">open ${escapeHtml(formatRelativeTime(g.openedAt))}</span></div>`).join('');
  return `<div class="gp-card gp-brain-details">
    <div class="gp-card-title">${escapeHtml(story.title || 'Untitled story')}</div>
    <div class="gp-card-meta" style="margin-top:4px"><span class="gp-sev ${severityChip(story.severity)}">${escapeHtml(story.severity || 'low')}</span><span>${escapeHtml(story.confidence || 'unverified')}</span><span>${escapeHtml(story.status || 'active')}</span>${story.region ? `<span>${escapeHtml(story.region)}</span>` : ''}</div>
    <div class="gp-tiny gp-muted" style="margin-top:6px">First seen ${escapeHtml(formatRelativeTime(story.firstSeen))} · last updated ${escapeHtml(formatRelativeTime(story.lastUpdated))} · completeness ${Math.round((story.completeness || 0) * 100)}%</div>
    ${actorChips ? `<div style="margin-top:8px"><div class="gp-tiny gp-muted">Actors</div><div class="gp-brain-summary" style="margin-top:4px">${actorChips}</div></div>` : ''}
    ${targetChips ? `<div style="margin-top:8px"><div class="gp-tiny gp-muted">Targets</div><div class="gp-brain-summary" style="margin-top:4px">${targetChips}</div></div>` : ''}
    ${gapRows ? `<div style="margin-top:10px"><div class="gp-tiny gp-muted">Missing pieces</div><div class="gp-stack" style="margin-top:6px">${gapRows}</div></div>` : ''}
    <div style="margin-top:10px;font-size:11px;font-weight:700">Evidence (${ev.length})</div>
    ${ev.length ? evidenceHtml(ev, evidenceLimit) : '<div class="gp-tiny gp-muted" style="margin-top:4px">No evidence records attached.</div>'}
    <div class="gp-row" style="margin-top:9px">
      <button class="gp-btn" type="button" data-story-link="map" data-story-hub="${escapeHtml(String(story.hubId || ''))}" data-story-title="${escapeHtml(story.title || '')}">Map</button>
      <button class="gp-btn" type="button" data-story-link="web" data-story-hub="${escapeHtml(String(story.hubId || ''))}" data-story-title="${escapeHtml(story.title || '')}">Web</button>
      <button class="gp-btn" type="button" data-story-link="timeline" data-story-hub="${escapeHtml(String(story.hubId || ''))}" data-story-title="${escapeHtml(story.title || '')}">Timeline</button>
      <button class="gp-btn" id="gpStoryClose" type="button">Close story</button>
    </div>
  </div>`;
}

function gapBoardHtml(gaps) {
  const open = gaps.filter(g => g.state !== 'closed');
  const byType = {};
  for (const gap of open) {
    const type = gap.type || 'other';
    byType[type] = byType[type] || { count: 0, severity: gap.severity };
    byType[type].count += 1;
  }
  const rows = Object.entries(byType).sort((a, b) => b[1].count - a[1].count).map(([type, info]) =>
    `<div class="gp-gap-row"><span class="gp-sev ${severityChip(info.severity)}">${escapeHtml(type)}</span><span class="grow">${info.count} stor${info.count === 1 ? 'y' : 'ies'} missing this</span></div>`).join('');
  const closedGaps = gaps.filter(g => g.state === 'closed').slice(0, 5);
  const closedRows = closedGaps.map(g => `<div class="gp-gap-row closed"><span class="gp-sev gp-sev-low">${escapeHtml(g.type)}</span><span class="grow">filled ${escapeHtml(formatRelativeTime(g.resolvedAt))}</span></div>`).join('');
  return `<div class="gp-stack">${rows || '<div class="gp-tiny gp-muted">No open gaps in the current story graph.</div>'}${closedRows ? `<div class="gp-tiny gp-muted" style="margin-top:6px">Recently filled</div>${closedRows}` : ''}</div>`;
}

function selectBrainNode(id, {scroll=true}={}) {
  selectedId = id ? String(id) : null;
  showAllEvidence = false;
  showAllRelationships = false;
  renderIntelligenceBrain();
  if (scroll) document.getElementById('brainBody')?.scrollIntoView({behavior:'smooth',block:'nearest'});
}

function matches(node) {
  const kind = String(node.kind || node.type || 'entity').toLowerCase();
  if (kindFilter !== 'all' && kind !== kindFilter) return false;
  if (!query) return true;
  const hay = [node.id,node.label,node.name,node.description,node.summary,node.country,node.region,node.group,kind].join(' ').toLowerCase();
  return hay.includes(query);
}

/* GUI Phase 4 — shared severity language for Brain kinds (never decorative):
 * conflict/cartel = critical, chokepoint = watch, economic/country/entity = info. */
function brainSeverity(kind) {
  const k = String(kind || '').toLowerCase();
  if (k === 'conflict' || k === 'cartel') return 'critical';
  if (k === 'chokepoint') return 'watch';
  return 'info';
}

function brainChip(kind) {
  const sev = brainSeverity(kind);
  if (sev === 'critical') return 'gp-sev-critical';
  if (sev === 'watch') return 'gp-sev-high';
  return 'gp-sev-medium';
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') return [value];
  return [];
}

function evidenceItems(record) {
  const candidates = [
    ...asArray(record?.evidence),
    ...asArray(record?.sources),
    ...asArray(record?.source),
    ...asArray(record?.provenance)
  ];
  const seen = new Set();
  return candidates.filter(item => {
    if (!item || typeof item !== 'object') return false;
    const url = String(item.url || item.href || '').trim();
    const title = String(item.title || item.name || item.source || '').trim();
    const key = url || `${title}|${String(item.time || item.publishedAt || '')}`;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return Boolean(url || title);
  });
}

function evidenceHtml(items, limit) {
  const visible = items.slice(0, limit);
  return visible.map(item => {
    const title = String(item.title || item.name || item.source || 'Source').trim();
    const source = String(item.source || item.publisher || '').trim();
    const time = String(item.time || item.publishedAt || item.date || '').trim();
    const url = String(item.url || item.href || '').trim();
    const meta = [source, time].filter(Boolean).join(' · ');
    const link = /^https?:\/\//i.test(url)
      ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);text-decoration:none">Open source ↗</a>`
      : '';
    return `<div style="margin-top:7px;padding:8px;border:1px solid var(--line);border-radius:8px;font-size:11px"><div style="font-weight:600">${escapeHtml(title)}</div>${meta?`<div style="color:var(--muted-2);margin-top:3px">${escapeHtml(meta)}</div>`:''}${link?`<div style="margin-top:4px">${link}</div>`:''}</div>`;
  }).join('');
}

function relationshipEvidence(edge) {
  return evidenceItems(edge);
}

function relationshipMeta(edge) {
  const values = [];
  const relationship = edge.relationship || edge.label || edge.type;
  if (relationship) values.push(String(relationship));
  const confidence = edge.confidence ?? edge.score ?? edge.strength;
  if (confidence !== undefined && confidence !== null && String(confidence) !== '') values.push(`confidence/strength: ${confidence}`);
  if (edge.reason) values.push(String(edge.reason));
  return values;
}

function relationshipType(edge) {
  return String(edge.relationship || edge.label || edge.type || 'relationship').trim().toLowerCase();
}

export function renderIntelligenceBrain() {
  const el = document.getElementById('brainBody');
  const updatedEl = document.getElementById('brainUpdated');
  if (!el) return;
  const { snapshot, intelligenceBrain, brainStories, brainGapHistory, status } = getState();
  const brain = intelligenceBrain || snapshot?.intelligenceBrain || null;
  if (!brain || !Array.isArray(brain.nodes)) {
    el.innerHTML = status === 'loading'
      ? '<div class="gp-state"><div class="gp-spinner"></div><div>Loading intelligence workspace…</div></div>'
      : '<div class="gp-state"><div class="gp-state-title">Intelligence Brain unavailable</div><div>The canonical brain artifact failed to load. Check source health below.</div></div>';
    return;
  }
  const nodes = brain.nodes;
  const edges = Array.isArray(brain.edges) ? brain.edges : [];
  const stats = brain.stats || {};
  if (updatedEl) updatedEl.textContent = formatRelativeTime(brain.updatedAt || snapshot?.updatedAt);
  const byId = new Map(nodes.map(n => [String(n.id), n]));
  const degree = {};
  edges.forEach(e => { const s=String(e.source||''), t=String(e.target||''); if(s)degree[s]=(degree[s]||0)+1; if(t)degree[t]=(degree[t]||0)+1; });
  const filtered = nodes.filter(matches);
  const ranked = [...filtered].sort((a,b)=>(degree[b.id]||0)-(degree[a.id]||0));
  const visible = showAll ? ranked : ranked.slice(0,5);
  const selected = selectedId ? byId.get(selectedId) : null;
  const allSelectedEdges = selected ? edges.filter(e => String(e.source)===selectedId || String(e.target)===selectedId) : [];
  const relationshipTypes = [...new Set(allSelectedEdges.map(relationshipType))].filter(Boolean).sort();
  const filteredSelectedEdges = allSelectedEdges.filter(e => relationshipFilter === 'all' || relationshipType(e) === relationshipFilter);
  const visibleSelectedEdges = showAllRelationships ? filteredSelectedEdges : filteredSelectedEdges.slice(0,5);
  const selectedEvidence = selected ? evidenceItems(selected) : [];
  const kinds = [...new Set(nodes.map(n => String(n.kind||n.type||'entity').toLowerCase()))].filter(Boolean).sort();
  const evidenceLimit = showAllEvidence ? 20 : 5;
  const stories = Array.isArray(brainStories?.stories) ? brainStories.stories : [];
  const gaps = Array.isArray(brainStories?.gaps) ? brainStories.gaps : [];
  const cycles = Array.isArray(brainGapHistory?.cycles) ? brainGapHistory.cycles : [];
  const lastCycle = cycles.length ? cycles[cycles.length - 1] : null;
  const rankedStories = stories.filter(s => storyMatches(s, query)).sort((a, b) => (Number(b.tensionContribution) || 0) - (Number(a.tensionContribution) || 0));
  const topStories = showAllStories ? rankedStories : rankedStories.slice(0, 5);
  const selectedStory = selectedStoryId ? stories.find(s => String(s.id) === String(selectedStoryId)) : null;
  el.innerHTML = `
    <div class="gp-brain-summary">
      <span class="gp-brain-chip">${nodes.length} nodes</span><span class="gp-brain-chip">${edges.length} relationships</span>
      <span class="gp-brain-chip">${Number(stats.marketIndicators||0)} market indicators</span><span class="gp-brain-chip">${Number(stats.countryNodes||0)} countries</span>
      <span class="gp-brain-chip">${Number(stats.economicNodes||0)} economic</span><span class="gp-brain-chip">${Number(stats.cartelNodes||0)} cartel/crime</span>
    </div>
    <div style="font-size:12px;color:var(--text-secondary);margin-bottom:10px">The Brain connects news, conflicts, geographic signals, events, claims, assessments, markets and macro context when public evidence supports the relationship. Connections are contextual relevance, not proof of causation, coordination or intent.</div>
    ${stories.length ? `<h3 class="gp-brief-h">What matters now</h3>
      <div class="gp-brain-summary">${deltaStripHtml(lastCycle)}</div>
      <div class="gp-stack" style="margin-top:8px">${topStories.map(s => storyCardHtml(s, gaps, String(selectedStoryId) === String(s.id))).join('') || '<div class="gp-tiny gp-muted">No stories match the search.</div>'}</div>
      ${rankedStories.length > 5 ? `<button id="gpStoryMore" class="gp-btn gp-more" type="button">${showAllStories ? 'Show fewer stories' : `Show all ${rankedStories.length} stories`}</button>` : ''}
      ${selectedStory ? storyDetailHtml(selectedStory, gaps, evidenceLimit) : ''}
      <h3 class="gp-brief-h">What we are missing</h3>${gapBoardHtml(gaps)}
      <h3 class="gp-brief-h">Major hubs</h3>`
      : '<div class="gp-honest" style="margin-bottom:10px">The Brain story graph is not published yet; it is generated by the next canonical refresh. The hub view below always reflects the canonical Brain artifact.</div>'}
    <div class="gp-brain-controls" style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px">
      <input id="gpBrainSearch" type="search" value="${escapeHtml(query)}" placeholder="Search the Brain…" style="flex:1;min-width:180px">
      <select id="gpBrainKind" style="min-height:34px;border:1px solid var(--line);border-radius:9px;background:var(--bg-elevated);color:var(--text);padding:7px 9px">
        <option value="all" ${kindFilter==='all'?'selected':''}>All types</option>${kinds.map(k=>`<option value="${escapeHtml(k)}" ${kindFilter===k?'selected':''}>${escapeHtml(k)}</option>`).join('')}
      </select>
      <button id="gpBrainClear" class="gp-btn" type="button">Clear</button>
    </div>
    <div style="font-size:10px;color:var(--muted-2);margin-bottom:7px">Showing ${visible.length} of ${ranked.length} matching nodes${query||kindFilter!=='all'?' · filtered':''}</div>
    <div class="gp-brain-grid">${visible.map(n=>`<button class="gp-card gp-brain-node sev-${brainSeverity(n.kind||n.type)} ${selectedId===String(n.id)?'selected':''}" data-brain-node="${escapeHtml(String(n.id))}" type="button"><div class="gp-card-title">${escapeHtml(n.label||n.name||n.id)}</div><div class="gp-card-meta"><span class="gp-sev ${brainChip(n.kind||n.type)}">${escapeHtml(n.kind||n.type||'entity')}</span><span>${degree[n.id]||0} links</span></div></button>`).join('')}</div>
    ${ranked.length===0 ? '<div class="gp-state" style="margin-top:8px">No Brain nodes match the current search/filter.</div>' : ''}
    ${ranked.length>5 ? `<button id="gpBrainMore" class="gp-btn" type="button" style="margin-top:9px;width:100%">${showAll?'Show fewer':'See more nodes'}</button>` : ''}
    ${selected ? `<div class="gp-card gp-brain-details">
      <div class="gp-card-title">${escapeHtml(selected.label||selected.name||selected.id)}</div>
      <div style="font-size:12px;color:var(--text-secondary);margin-top:6px">${escapeHtml(selected.description||selected.summary||'No additional description in the current evidence artifact.')}</div>
      ${selected.actionCounts ? `<div style="margin-top:9px"><div class="gp-tiny gp-muted">Source-backed action evidence (${escapeHtml(String(selected.actionEvidenceCount || 0))} records)</div><div class="gp-brain-summary" style="margin-top:5px">${Object.entries(selected.actionCounts).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([k,v])=>`<span class="gp-brain-chip">${escapeHtml(k)} ${Number(v)}</span>`).join('')}</div><div class="gp-tiny gp-muted" style="margin-top:4px">Action counts are evidence volumes, not measures of intent or impact.</div></div>` : ''}
      <div style="margin-top:10px;font-size:11px;font-weight:700">Source-backed evidence (${selectedEvidence.length})</div>
      ${selectedEvidence.length ? evidenceHtml(selectedEvidence,evidenceLimit) : '<div style="font-size:11px;color:var(--muted-2);margin-top:5px">No evidence records are attached to this node.</div>'}
      ${selectedEvidence.length>5 ? `<button id="gpBrainEvidenceMore" class="gp-btn" type="button" style="margin-top:7px;width:100%">${showAllEvidence?'Show fewer evidence items':'See more evidence'}</button>` : ''}
      <div style="margin-top:11px;font-size:11px;font-weight:700">Relationships (${filteredSelectedEdges.length}${filteredSelectedEdges.length>5?' · showing '+visibleSelectedEdges.length:''})</div>
      ${relationshipTypes.length>1 ? `<div style="display:flex;gap:7px;align-items:center;margin-top:7px"><select id="gpBrainRelationshipFilter" style="width:100%;min-height:34px;border:1px solid var(--line);border-radius:9px;background:var(--bg-elevated);color:var(--text);padding:7px 9px"><option value="all" ${relationshipFilter==='all'?'selected':''}>All relationship types</option>${relationshipTypes.map(k=>`<option value="${escapeHtml(k)}" ${relationshipFilter===k?'selected':''}>${escapeHtml(k)}</option>`).join('')}</select></div>` : ''}
      ${visibleSelectedEdges.map(e=>{
        const other=String(e.source)===selectedId?byId.get(String(e.target)):byId.get(String(e.source));
        const meta=relationshipMeta(e);
        const ev=relationshipEvidence(e);
        return `<div style="margin-top:7px;padding:8px;border:1px solid var(--line);border-radius:8px;font-size:11px"><strong>${escapeHtml(other?.label||other?.name||'Connected signal')}</strong>${meta.length?`<div style="color:var(--text-secondary);margin-top:3px">${escapeHtml(meta.join(' · '))}</div>`:''}${ev.length?`<div style="margin-top:5px">${evidenceHtml(ev,3)}</div>`:''}</div>`;
      }).join('')}
      ${filteredSelectedEdges.length>5 ? `<button id="gpBrainRelationshipsMore" class="gp-btn" type="button" style="margin-top:7px;width:100%">${showAllRelationships?'Show fewer relationships':'See more relationships'}</button>` : ''}
      <div class="gp-row" style="margin-top:9px"><button class="gp-btn" id="brainClearSelection" type="button">Close node</button><button class="gp-btn" type="button" data-hub-link="map" data-hub-id="${escapeHtml(selectedId||'')}">View on map</button><button class="gp-btn" type="button" data-hub-link="web" data-hub-id="${escapeHtml(selectedId||'')}">View in Web</button></div>
    </div>` : ''}
    <div style="margin-top:10px;font-size:10px;color:var(--muted-2)">Source-backed only: ${brain.sourceBackedOnly===true?'YES':'NO'} · Consolidated: ${brain.consolidated===true?'YES':'NO'}</div>`;

  el.querySelectorAll('[data-brain-node]').forEach(btn=>btn.addEventListener('click',()=>{
    const id=btn.dataset.brainNode;
    relationshipFilter='all';
    selectBrainNode(id);
    window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id,source:'brain'}}));
  }));
  el.querySelector('#brainClearSelection')?.addEventListener('click',()=>{selectedId=null;relationshipFilter='all';showAllEvidence=false;showAllRelationships=false;window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id:null,source:'brain'}}));renderIntelligenceBrain();});
  el.querySelector('#gpBrainEvidenceMore')?.addEventListener('click',()=>{showAllEvidence=!showAllEvidence;renderIntelligenceBrain();});
  el.querySelector('#gpBrainRelationshipsMore')?.addEventListener('click',()=>{showAllRelationships=!showAllRelationships;renderIntelligenceBrain();});
  el.querySelector('#gpBrainRelationshipFilter')?.addEventListener('change',event=>{relationshipFilter=String(event.target.value||'all');showAllRelationships=false;renderIntelligenceBrain();});
  el.querySelector('#gpBrainSearch')?.addEventListener('input',event=>{query=String(event.target.value||'').trim().toLowerCase();showAll=false;renderIntelligenceBrain();const input=document.getElementById('gpBrainSearch');input?.focus();input?.setSelectionRange(input.value.length,input.value.length);});
  el.querySelector('#gpBrainKind')?.addEventListener('change',event=>{kindFilter=String(event.target.value||'all');showAll=false;renderIntelligenceBrain();});
  el.querySelector('#gpBrainClear')?.addEventListener('click',()=>{query='';kindFilter='all';showAll=false;renderIntelligenceBrain();});
  el.querySelector('#gpBrainMore')?.addEventListener('click',()=>{showAll=!showAll;renderIntelligenceBrain();});
  el.querySelectorAll('[data-story]').forEach(btn=>btn.addEventListener('click',()=>{selectedStoryId=selectedStoryId===btn.dataset.story?null:btn.dataset.story;renderIntelligenceBrain();}));
  el.querySelector('#gpStoryMore')?.addEventListener('click',()=>{showAllStories=!showAllStories;renderIntelligenceBrain();});
  el.querySelector('#gpStoryClose')?.addEventListener('click',()=>{selectedStoryId=null;renderIntelligenceBrain();});
  el.querySelectorAll('[data-story-link]').forEach(btn=>btn.addEventListener('click',()=>{const id=btn.dataset.storyHub||'';const label=btn.dataset.storyTitle||'';if(id||label)window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id,label,source:'brain'}}));const target=btn.dataset.storyLink;try{window.location.hash=target==='web'?'#section-intelweb':target==='timeline'?'#section-timeline':'#section-map'}catch{}}));
  el.querySelectorAll('[data-hub-link]').forEach(btn=>btn.addEventListener('click',()=>{const id=btn.dataset.hubId||'';if(id)window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id,source:'brain'}}));const target=btn.dataset.hubLink;try{window.location.hash=target==='web'?'#section-intelweb':'#section-map'}catch{}}));
}

window.addEventListener('gp:brain-select', event => {
  const id = event.detail?.id;
  if (!id || event.detail?.source === 'brain') return;
  selectBrainNode(String(id), {scroll:false});
});
