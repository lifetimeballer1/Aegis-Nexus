/** Intelligence Brain timeline — evidence-linked temporal context for selected nodes. */
import { getState } from '../core/state.js';
import { escapeHtml, formatRelativeTime } from '../core/utils.js';

let selectedId = null;
let showAll = false;

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') return [value];
  return [];
}

function timeOf(item) {
  const raw = item?.time || item?.publishedAt || item?.timestamp || item?.date || item?.updatedAt || '';
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? null : d;
}

function textOf(item) {
  return [item?.title,item?.name,item?.label,item?.summary,item?.description,item?.reason].filter(Boolean).join(' ');
}

function evidenceOf(record) {
  return [...asArray(record?.evidence), ...asArray(record?.sources), ...asArray(record?.source), ...asArray(record?.provenance)]
    .filter(x => x && typeof x === 'object');
}

function relatedChanges(snapshot, selected) {
  const changes = snapshot?.whatChanged || snapshot?.what_changed || snapshot?.changes || {};
  const raw = asArray(changes?.items).concat(asArray(changes?.changes), asArray(changes?.events));
  const nodeTerms = selected ? [selected.id,selected.label,selected.name].filter(Boolean).map(String).map(x=>x.toLowerCase()) : [];
  return raw.filter(item => {
    if (!timeOf(item)) return false;
    if (!selected) return true;
    const hay = textOf(item).toLowerCase();
    return nodeTerms.some(term => term && hay.includes(term));
  }).map(item => ({item,date:timeOf(item), evidence:evidenceOf(item)}));
}

function selectedEvidence(snapshot, selected) {
  if (!selected) return [];
  return evidenceOf(selected).map(item => ({item,date:timeOf(item),evidence:[]})).filter(x=>x.date);
}

function render() {
  const host = document.getElementById('brainBody');
  if (!host) return;
  host.querySelector('#gpBrainTimeline')?.remove();
  const { snapshot } = getState();
  const brain = snapshot?.intelligenceBrain;
  if (!brain?.nodes?.length) return;
  const node = selectedId ? brain.nodes.find(n => String(n.id)===String(selectedId)) : null;
  const rows = relatedChanges(snapshot,node);
  const fallback = selectedEvidence(snapshot,node);
  const combined = [...rows];
  fallback.forEach(x => {
    const key = `${x.date.toISOString()}|${textOf(x.item)}`;
    if (!combined.some(y=>`${y.date.toISOString()}|${textOf(y.item)}`===key)) combined.push(x);
  });
  combined.sort((a,b)=>b.date-a.date);
  const visible = showAll ? combined : combined.slice(0,5);
  const title = node ? `Temporal context · ${node.label || node.name || node.id}` : 'Recent intelligence timeline';
  const subtitle = node ? 'Only changes or evidence explicitly mentioning the selected Brain node are shown.' : 'Select a Brain node to focus the timeline on that entity.';
  const wrap = document.createElement('section');
  wrap.id='gpBrainTimeline';
  wrap.style.cssText='margin-top:12px;padding:11px;border:1px solid var(--line);border-radius:10px;background:var(--bg-elevated)';
  wrap.innerHTML=`<div style="font-size:12px;font-weight:700">${escapeHtml(title)}</div><div style="font-size:10px;color:var(--muted-2);margin-top:3px">${escapeHtml(subtitle)}</div>${visible.length ? visible.map(({item,date,evidence})=>{
    const title=textOf(item)||'Intelligence update';
    const source=item?.source||item?.publisher||'';
    const url=item?.url||item?.href||evidence?.[0]?.url||'';
    const link=/^https?:\/\//i.test(url)?`<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" style="color:var(--sev-info);text-decoration:none">Source ↗</a>`:'';
    return `<div style="margin-top:7px;padding:8px;border-left:2px solid var(--sev-info);background:var(--bg);border-radius:7px"><div style="font-size:11px;font-weight:600">${escapeHtml(title)}</div><div style="font-size:10px;color:var(--muted-2);margin-top:3px">${escapeHtml(date.toISOString())}${source?` · ${escapeHtml(source)}`:''}</div>${link?`<div style="margin-top:4px;font-size:10px">${link}</div>`:''}</div>`;
  }).join(''):`<div style="font-size:11px;color:var(--muted-2);margin-top:7px">No explicitly time-stamped evidence or change record is linked to this node in the current artifact.</div>`}${combined.length>5?`<button id="gpBrainTimelineMore" class="gp-btn" type="button" style="margin-top:8px;width:100%">${showAll?'Show fewer':'See more timeline items'}</button>`:''}`;
  host.appendChild(wrap);
  wrap.querySelector('#gpBrainTimelineMore')?.addEventListener('click',()=>{showAll=!showAll;render();});
}

export function renderBrainTimeline() { render(); }

window.addEventListener('gp:brain-select', event => {
  selectedId = event.detail?.id ? String(event.detail.id) : null;
  showAll=false;
  render();
});
