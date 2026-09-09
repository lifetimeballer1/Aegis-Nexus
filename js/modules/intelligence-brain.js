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
  if (sev === 'watch') return 'gp-sev-watch';
  if (sev === 'healthy') return 'gp-sev-healthy';
  return 'gp-sev-info';
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
      ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" style="color:var(--sev-info);text-decoration:none">Open source ↗</a>`
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
  const { snapshot, intelligenceBrain, status } = getState();
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
  el.innerHTML = `
    <div class="gp-brain-summary">
      <span class="gp-brain-chip">${nodes.length} nodes</span><span class="gp-brain-chip">${edges.length} relationships</span>
      <span class="gp-brain-chip">${Number(stats.marketIndicators||0)} market indicators</span><span class="gp-brain-chip">${Number(stats.countryNodes||0)} countries</span>
      <span class="gp-brain-chip">${Number(stats.economicNodes||0)} economic</span><span class="gp-brain-chip">${Number(stats.cartelNodes||0)} cartel/crime</span>
    </div>
    <div style="font-size:12px;color:var(--text-secondary);margin-bottom:10px">The Brain connects news, conflicts, geographic signals, events, claims, assessments, markets and macro context when public evidence supports the relationship. Connections are contextual relevance, not proof of causation, coordination or intent.</div>
    <div class="gp-brain-controls" style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px">
      <input id="gpBrainSearch" type="search" aria-label="Search the Brain" value="${escapeHtml(query)}" placeholder="Search the Brain…" style="flex:1;min-width:180px">
      <select id="gpBrainKind" style="min-height:34px;border:1px solid var(--line);border-radius:9px;background:var(--bg-elevated);color:var(--text);padding:7px 9px">
        <option value="all" ${kindFilter==='all'?'selected':''}>All types</option>${kinds.map(k=>`<option value="${escapeHtml(k)}" ${kindFilter===k?'selected':''}>${escapeHtml(k)}</option>`).join('')}
      </select>
      <button id="gpBrainClear" class="gp-btn" type="button">Clear</button>
    </div>
    <div style="font-size:10px;color:var(--muted-2);margin-bottom:7px">Showing ${visible.length} of ${ranked.length} matching nodes${query||kindFilter!=='all'?' · filtered':''}</div>
    <div class="gp-brain-grid">${visible.map(n=>`<button class="gp-card gp-brain-node sev-${brainSeverity(n.kind||n.type)} ${selectedId===String(n.id)?'selected':''}" data-brain-node="${escapeHtml(String(n.id))}" type="button"><div class="gp-card-title">${escapeHtml(n.label||n.name||n.id)}</div><div class="gp-card-meta"><span class="gp-sev ${brainChip(n.kind||n.type)}">${escapeHtml(n.kind||n.type||'entity')}</span><span>${degree[n.id]||0} links</span></div></button>`).join('')}</div>
    ${ranked.length===0 ? '<div class="gp-state" style="margin-top:8px"><div class="gp-state-title">No matching nodes</div><div>No Brain nodes match the current search/filter.</div></div>' : ''}
    ${ranked.length>5 ? `<button id="gpBrainMore" class="gp-btn" type="button" style="margin-top:9px;width:100%">${showAll?'Show fewer':'See more nodes'}</button>` : ''}
    ${selected ? `<div class="gp-card gp-brain-details">
      <div class="gp-card-title">${escapeHtml(selected.label||selected.name||selected.id)}</div>
      <div style="font-size:12px;color:var(--text-secondary);margin-top:6px">${escapeHtml(selected.description||selected.summary||'No additional description in the current evidence artifact.')}</div>
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
      <button class="gp-btn" id="brainClearSelection" type="button" style="margin-top:9px">Close node</button>
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
}

window.addEventListener('gp:brain-select', event => {
  const id = event.detail?.id;
  if (!id || event.detail?.source === 'brain') return;
  selectBrainNode(String(id), {scroll:false});
});
