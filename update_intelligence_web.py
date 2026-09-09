#!/usr/bin/env python3
"""Build the Intelligence Web from canonical intelligence."""
import json
from datetime import datetime, timezone
from pathlib import Path
from intelligence_schema import validate_document, SCHEMA_VERSION
ROOT=Path(__file__).resolve().parent; SNAP=ROOT/'data'/'snapshot.json'; CANONICAL=ROOT/'data'/'canonical_intelligence.json'

def evidence_from(r):
    if not isinstance(r,dict): return None
    title=str(r.get('title') or r.get('name') or 'Public intelligence record').strip(); url=str(r.get('url') or r.get('original_link') or r.get('sourceUrl') or r.get('source_url') or r.get('link') or '').strip(); source=str(r.get('source') or r.get('sourceLabel') or r.get('publisher') or 'Public source').strip(); time=str(r.get('published_at') or r.get('publishedAt') or r.get('published_date') or r.get('time') or r.get('updatedAt') or '').strip(); summary=str(r.get('excerpt') or r.get('summary') or r.get('description') or r.get('summary_snippet') or '').strip()
    return {'title':title,'url':url,'source':source,'time':time,'summary':summary[:420]} if title or url else None

def main():
    if not CANONICAL.exists(): raise SystemExit('GRAPH BLOCKED: canonical_intelligence.json unavailable')
    try: canonical=json.loads(CANONICAL.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc: raise SystemExit(f'GRAPH BLOCKED: invalid canonical JSON: {exc}')
    errors=validate_document(canonical)
    if errors: raise SystemExit(f'GRAPH BLOCKED: canonical schema validation failed ({len(errors)} errors)')
    if canonical.get('schema_version')!=SCHEMA_VERSION: raise SystemExit('GRAPH BLOCKED: incompatible canonical schema')
    evidence={str(x.get('id')):x for x in canonical.get('evidence',[]) if isinstance(x,dict) and x.get('id')}; nodes={}
    for e in canonical.get('entities',[]):
        if not isinstance(e,dict) or not e.get('id') or not e.get('canonical_name'): continue
        nid=str(e['id']); nodes[nid]={'id':nid,'label':str(e['canonical_name']),'kind':str(e.get('entity_type') or 'other'),'mentions':int(e.get('mention_count') or 0),'importance':float(e.get('importance') or 0),'evidence':[]}
        for eid in e.get('evidence_ids',[])[:12]:
            ev=evidence_from(evidence.get(str(eid)))
            if ev: nodes[nid]['evidence'].append(ev)
    edges={}
    def add_edge(s,t,relation,confidence,weight,event_ids,evidence_ids):
        if s not in nodes or t not in nodes or s==t: return
        evs=[evidence_from(evidence.get(str(x))) for x in evidence_ids[:8]]; evs=[x for x in evs if x]
        if not evs: return
        key=f'{s}|{relation}|{t}'; edge=edges.setdefault(key,{'source':s,'target':t,'weight':0.,'types':[],'relationship':relation,'confidence':0.,'strength':0.,'eventIds':[],'evidence':[],'evidenceCount':0})
        edge['weight']+=max(.25,float(weight or 1)); edge['confidence']=max(edge['confidence'],float(confidence or 0))
        if relation not in edge['types']: edge['types'].append(relation)
        edge['eventIds'] += [str(x) for x in event_ids if str(x) not in edge['eventIds']]
        for ev in evs:
            if not any(x.get('title')==ev.get('title') for x in edge['evidence']) and len(edge['evidence'])<8: edge['evidence'].append(ev)
        edge['evidenceCount']=len(edge['evidence']); edge['strength']=max(edge['strength'],edge['confidence']*min(1.,edge['weight']/10.))
    for r in canonical.get('relationships',[]):
        if isinstance(r,dict): add_edge(str(r.get('source_entity_id') or ''),str(r.get('target_entity_id') or ''),str(r.get('relationship_type') or 'other'),r.get('confidence'),r.get('weight') or r.get('strength'),r.get('event_ids',[]),r.get('evidence_ids',[]))
    event_rel={'military_action':'military_action_against','sanction':'sanctions','trade_action':'trades_with','diplomatic_action':'negotiates_with','economic_action':'affects','technology_action':'affects','energy_action':'affects','cyber_activity':'targets','political_action':'affects','conflict_event':'opposes'}
    for event in canonical.get('events',[]):
        if not isinstance(event,dict): continue
        relation=event_rel.get(str(event.get('event_type') or ''))
        if not relation: continue
        for actor in event.get('actor_ids',[]):
            for target in event.get('target_ids',[]): add_edge(str(actor),str(target),relation,event.get('confidence'),event.get('score') or 1,[event.get('id')] if event.get('id') else [],event.get('evidence_ids',[]))
    edge_list=list(edges.values()); degree={nid:0. for nid in nodes}
    for e in edge_list: degree[e['source']]+=e['weight']; degree[e['target']]+=e['weight']
    for n in nodes.values(): n['graphImportance']=round(n['importance']+degree.get(n['id'],0),4)
    node_list=sorted(nodes.values(),key=lambda x:(x['graphImportance'],x['mentions'],x['label']),reverse=True)[:100]; allowed={n['id'] for n in node_list}; edge_list=[e for e in edge_list if e['source'] in allowed and e['target'] in allowed]; edge_list.sort(key=lambda x:(x['strength'],x['weight'],x['evidenceCount']),reverse=True); edge_list=edge_list[:500]
    output={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'method':'canonical intelligence events and evidence-backed semantic relationships','caution':'Semantic edges are generated from structured event actor/target roles; evidence-backed associations do not independently prove causation, coordination, alliance, or responsibility.','sourceSchemaVersion':canonical.get('schema_version'),'nodes':node_list,'edges':edge_list}
    snapshot=json.loads(SNAP.read_text(encoding='utf-8')); snapshot['intelligenceGraph']=output; SNAP.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Intelligence graph: {len(node_list)} canonical nodes / {len(edge_list)} evidence-backed edges')
if __name__=='__main__': main()
