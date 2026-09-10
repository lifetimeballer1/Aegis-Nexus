#!/usr/bin/env python3
"""Repair Brain group coverage from source-backed repository data without inventing evidence."""
from __future__ import annotations
import json,re,math
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data'
BRAIN=DATA/'intelligence_brain.json';SNAP=DATA/'snapshot.json'
COUNTRIES={'United States':(38,-97),'Mexico':(23.6,-102.5),'Colombia':(4.6,-74.1),'Ecuador':(-1.4,-78.4),'Venezuela':(7.1,-66),'Brazil':(-10.8,-52.9),'El Salvador':(13.8,-88.9)}
CARTELS={'Sinaloa Cartel':'Mexico','CJNG':'Mexico','Jalisco New Generation Cartel':'Mexico','Gulf Cartel':'Mexico','Los Zetas':'Mexico','Northeast Cartel':'Mexico','Santa Rosa de Lima Cartel':'Mexico','La Nueva Familia Michoacana':'Mexico','Juarez Cartel':'Mexico','Beltran Leyva Organization':'Mexico','Clan del Golfo':'Colombia','Tren de Aragua':'Venezuela','PCC':'Brazil','Primeiro Comando da Capital':'Brazil','Comando Vermelho':'Brazil','Los Choneros':'Ecuador','MS-13':'El Salvador','Mara Salvatrucha':'El Salvador'}
STRATEGIC_COUNTRIES={'united states','usa','china','people’s republic of china','peoples republic of china','mexico','russia','india','iran','israel'}
def slug(x):return re.sub(r'[^a-z0-9]+','-',str(x).lower()).strip('-')
def evidence(r):
 if not isinstance(r,dict): return None
 title=str(r.get('title') or r.get('name') or r.get('headline') or r.get('label') or r.get('description') or '').strip()
 url=str(r.get('original_link') or r.get('url') or r.get('sourceUrl') or r.get('source_url') or r.get('link') or '').strip()
 source=str(r.get('sourceLabel') or r.get('source') or r.get('publisher') or r.get('provider') or '').strip()
 if title and (url or source): return {'title':title[:300],'url':url,'source':source or 'Public source','time':str(r.get('publishedAt') or r.get('published_date') or r.get('updatedAt') or r.get('time') or '')}
 return None
def evidence_key(ev):
 return (str(ev.get('title') or '').strip().lower(),str(ev.get('url') or '').strip().lower(),str(ev.get('source') or '').strip().lower())
def add_unique(items, ev):
 if ev and evidence_key(ev) not in {evidence_key(x) for x in items}: items.append(ev)
def walk(obj):
 if isinstance(obj,dict):
  yield obj
  for v in obj.values(): yield from walk(v)
 elif isinstance(obj,list):
  for v in obj: yield from walk(v)
def rank(n):
 text=str(n.get('label') or '').strip().lower(); ev=len(n.get('evidence') or []); mentions=int(n.get('mentions') or 0); score=float(n.get('score') or 0)
 strategic=28 if text in STRATEGIC_COUNTRIES else 0
 kind_bonus={'country':8,'conflict':6,'economic':5,'chokepoint':4,'cartel':4}.get(str(n.get('kind') or '').lower(),0)
 return strategic+kind_bonus+score*2+math.log1p(ev)*7+math.log1p(mentions)*4
def annotate_tension_truth(snap):
 """Honest tension metadata: derive when the published tension block was
 actually computed instead of implying it refreshed with the snapshot.
 The canonical tension writer (build_tension.py) overwrites these fields
 with tensionStale=False on every real recomputation."""
 computed=None
 try:
  hist=json.loads((DATA/'history.json').read_text(encoding='utf-8'))
  if isinstance(hist,list):
   for row in reversed(hist):
    if isinstance(row,dict) and row.get('tension')==snap.get('tension'):
     computed=row.get('updatedAt');break
   if not computed and hist:computed=hist[-1].get('updatedAt')
 except Exception:pass
 if not computed:computed=str(snap.get('tensionComputedAt') or (snap.get('freshness') or {}).get('generatedAt') or '')
 snap['tensionComputedAt']=computed
 age=None
 if computed:
  try:
   dt=datetime.fromisoformat(str(computed).replace('Z','+00:00'))
   age=(datetime.now(timezone.utc)-dt).total_seconds()/3600
  except Exception:age=None
 snap['tensionStale']=bool(age is None or age>6)
 return snap
def main():
 brain=json.loads(BRAIN.read_text(encoding='utf-8'));snap=json.loads(SNAP.read_text(encoding='utf-8'))
 nodes=brain.setdefault('nodes',[]);edges=brain.setdefault('edges',[]);by={str(n.get('id')):n for n in nodes}
 records=list(walk(snap));graph=snap.get('intelligenceGraph') or {};records += list(walk(graph))
 for fn in ('live_articles.json','event_intelligence.json','claims.json','intelligence_assessment.json','event_market_impact.json','what_changed.json'):
  p=DATA/fn
  if p.exists():
   try: records += list(walk(json.loads(p.read_text(encoding='utf-8'))))
   except Exception: pass
 for gn in graph.get('nodes') or []: records.append(gn)
 for label,country in CARTELS.items():
  if any(n.get('kind')=='cartel' and str(n.get('label'))==label for n in nodes): continue
  hits=[];seen=set()
  for r in records:
   ev=evidence(r)
   if not ev: continue
   key=evidence_key(ev)
   if key in seen: continue
   blob=' '.join(str(r.get(k,'')) for k in ('label','name','title','headline','summary','description','detail','actor','actors','organization','organizations','group','category','type','tags','keywords','country','location')).lower()
   if re.search(r'(?<![a-z])'+re.escape(label.lower())+r'(?![a-z])',blob): hits.append(ev);seen.add(key)
  if hits:
   lat,lng=COUNTRIES[country];i=slug(label);n={'id':i,'label':label,'kind':'cartel','score':7,'mentions':len(hits),'evidence':hits[:5],'canonical':True,'country':country,'lat':lat,'lng':lng,'group':'Organized Crime'};nodes.append(n);by[i]=n
 required_kinds=('cartel','country','economic','conflict','chokepoint')
 for kind in required_kinds:
  if not any(n.get('kind')==kind for n in nodes): raise RuntimeError(f'unable to retain a source-backed {kind} node')
 required=[]
 for kind in required_kinds:
  candidates=[n for n in nodes if n.get('kind')==kind];candidates.sort(key=rank,reverse=True);required.append(candidates[0])
 required_ids={id(n) for n in required}
 rest=[n for n in nodes if id(n) not in required_ids];rest.sort(key=rank,reverse=True)
 # Preserve evidence-backed strategic countries such as the United States and China whenever they exist in the source-backed pool.
 strategic=[n for n in rest if str(n.get('kind') or '').lower()=='country' and str(n.get('label') or '').strip().lower() in STRATEGIC_COUNTRIES]
 strategic.sort(key=rank,reverse=True)
 selected=required[:]
 for n in strategic:
  if n not in selected and len(selected)<35: selected.append(n)
 for n in rest:
  if n not in selected and len(selected)<35: selected.append(n)
 nodes=selected[:35];keep={n.get('id') for n in nodes};brain['nodes']=nodes
 brain['edges']=[e for e in edges if e.get('source') in keep and e.get('target') in keep and e.get('evidence')]
 stats=brain.setdefault('stats',{});stats.update({'nodes':len(nodes),'edges':len(brain['edges']),'cartelNodes':sum(n.get('kind')=='cartel' for n in nodes),'countryNodes':sum(n.get('kind')=='country' for n in nodes),'economicNodes':sum(n.get('kind')=='economic' for n in nodes),'conflictNodes':sum(n.get('kind')=='conflict' for n in nodes),'chokepointNodes':sum(n.get('kind')=='chokepoint' for n in nodes)})
 now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
 brain['updatedAt']=now
 BRAIN.write_text(json.dumps(brain,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 snap['intelligenceBrain']=brain
 snap['updatedAt']=now
 snap['lastSuccessfulRefresh']=now
 annotate_tension_truth(snap)
 SNAP.write_text(json.dumps(snap,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 print(f"BRAIN GROUP REPAIR: {len(nodes)} nodes / {len(brain['edges'])} edges / cartels={stats['cartelNodes']} countries={stats['countryNodes']} economic={stats['economicNodes']} conflicts={stats['conflictNodes']} chokepoints={stats['chokepointNodes']}")
if __name__=='__main__':main()
