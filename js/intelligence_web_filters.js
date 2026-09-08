/* Presentation filters for the canonical graph; never infer new relationships. */
(function(root){
'use strict';
const categories={
  country:['country'], person:['person'],
  government:['government','government_agency','political_party'],
  military:['military','military_command','intelligence','armed_group'],
  organization:['international_organization'],
  economic:['company','financial_institution'],
  location:['location','region'], conflict:['conflict'],
  infrastructure:['infrastructure'], technology:['technology'], other:['other']
};
const endpoint=value=>String(value?.id??value??'');
function project(base,{query='',category='all',period='all',now=Date.now()}={}){
  const hours=Number(period),limited=period!=='all'&&Number.isFinite(hours)&&hours>0;
  const cutoff=now-hours*3600000;
  const evidenceFor=item=>(item.evidence||[]).filter(e=>{
    if(!limited)return true;
    const time=Date.parse(e.time||e.published_at||e.published_date||'');
    return Number.isFinite(time)&&time>=cutoff&&time<=now;
  });
  const nodes=(base.nodes||[]).map(n=>({...n,evidence:evidenceFor(n)}));
  const valid=new Set(nodes.map(n=>String(n.id)));
  const links=(base.links||[]).map(e=>({...e,source:endpoint(e.source),target:endpoint(e.target),evidence:evidenceFor(e)}))
    .filter(e=>valid.has(e.source)&&valid.has(e.target)&&(!limited||e.evidence.length));
  const eligible=new Set(nodes.filter(n=>!limited||n.evidence.length).map(n=>String(n.id)));
  links.forEach(e=>{eligible.add(e.source);eligible.add(e.target)});
  const q=query.trim().toLowerCase();
  const focus=nodes.filter(n=>eligible.has(String(n.id))&&
    (category==='all'||(categories[category]||[category]).includes(n.kind))&&
    (!q||[n.label,n.id,n.canonical_name,...(n.aliases||[])].some(s=>String(s||'').toLowerCase().includes(q))));
  const ids=new Set(focus.map(n=>String(n.id))),keep=new Set(ids);
  const visibleLinks=links.filter(e=>ids.has(e.source)||ids.has(e.target));
  visibleLinks.forEach(e=>{keep.add(e.source);keep.add(e.target)});
  return {nodes:nodes.filter(n=>keep.has(String(n.id))),links:visibleLinks,focus};
}
const api={categories,project};
if(typeof module==='object'&&module.exports)module.exports=api;
else root.IntelligenceWebFilters=api;
})(typeof window==='undefined'?globalThis:window);
