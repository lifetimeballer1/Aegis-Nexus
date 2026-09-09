#!/usr/bin/env python3
"""Guarantee source-backed United States and China hubs survive Brain compaction."""
from __future__ import annotations
import json,re,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; BRAIN=DATA/'intelligence_brain.json'
ALIASES={
 'United States': [r'\bunited states\b',r'\bu\.s\.a?\.?\b',r'\busa\b',r'\bamerican\b',r'\bamerica\b',r'\bwashington\b',r'\bwhite house\b',r'\bpentagon\b'],
 'China': [r'\bchina\b',r'\bchinese\b',r'\bbeijing\b',r'\bpla\b',r"\bpeople.?s republic of china\b",r'\bccp\b']}
COORDS={'United States':(38.0,-97.0),'China':(35.9,104.2)}

def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values(): yield from walk(v)
 elif isinstance(x,list):
  for v in x: yield from walk(v)
def ev(r):
 if not isinstance(r,dict): return None
 title=str(r.get('title') or r.get('headline') or r.get('name') or r.get('label') or r.get('description') or '').strip()
 url=str(r.get('url') or r.get('original_link') or r.get('sourceUrl') or r.get('source_url') or r.get('link') or '').strip()
 source=str(r.get('source') or r.get('sourceLabel') or r.get('publisher') or r.get('provider') or '').strip()
 if not title or not (url or source): return None
 return {'title':title[:300],'url':url,'source':source or 'Public source','time':str(r.get('publishedAt') or r.get('published_date') or r.get('updatedAt') or r.get('time') or '')}
def key(e): return (e['title'].lower(),e['url'].lower(),e['source'].lower())
def main():
 brain=json.loads(BRAIN.read_text(encoding='utf-8')); nodes=brain.setdefault('nodes',[])
 records=[]
 for fn in ('live_articles.json','intelligence_graph.json','claims.json','intelligence_assessment.json','event_intelligence.json','what_changed.json'):
  p=DATA/fn
  if p.exists():
   try: records.extend(walk(json.loads(p.read_text(encoding='utf-8'))))
   except Exception: pass
 for actor,patterns in ALIASES.items():
  existing=next((n for n in nodes if str(n.get('label'))==actor),None)
  if existing is None:
   evidence=[]; seen=set()
   for r in records:
    text=' '.join(str(r.get(k,'')) for k in ('title','headline','summary_snippet','summary','description','content','detail','name','country','location','category','type','tags','keywords','actor','actors','organization','organizations','group','text')).lower()
    if not any(re.search(p,text) for p in patterns): continue
    item=ev(r)
    if item and key(item) not in seen:
     evidence.append(item);seen.add(key(item))
     if len(evidence)>=100: break
   if not evidence:
    print(f'ERROR: no source-backed evidence found for {actor}'); return 1
   lat,lng=COORDS[actor]
   existing={'id':actor.lower().replace(' ','-'),'label':actor,'kind':'country','score':100,'mentions':len(evidence),'evidence':evidence,'country':actor,'lat':lat,'lng':lng,'group':'Strategic Actor','canonical':True}
   nodes.append(existing)
  else:
   existing['kind']='country';existing['canonical']=True;existing['lat'],existing['lng']=COORDS[actor];existing['country']=actor;existing['group']='Strategic Actor'
  # Make major-power hubs structurally sticky: remove the lowest-score non-major node if over the 35-node cap.
  if len(nodes)>35:
   removable=[n for n in nodes if n.get('label') not in ALIASES]
   removable.sort(key=lambda n:(float(n.get('score') or 0),len(n.get('evidence') or []),int(n.get('mentions') or 0)))
   if removable: nodes.remove(removable[0])
 keep={n.get('id') for n in nodes}; brain['edges']=[e for e in brain.get('edges',[]) if e.get('source') in keep and e.get('target') in keep and e.get('evidence')]
 stats=brain.setdefault('stats',{});stats['nodes']=len(nodes);stats['edges']=len(brain['edges']);stats['countryNodes']=sum(n.get('kind')=='country' for n in nodes)
 now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z');brain['version']=max(int(brain.get('version') or 0),12);brain['updatedAt']=now;brain['majorPowerPolicy']={'required':['United States','China'],'sourceBackedOnly':True,'purpose':'Prevent major strategic actor hubs from disappearing during graph compaction.'}
 BRAIN.write_text(json.dumps(brain,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
 print('MAJOR POWER GATE:','; '.join(f"{a}=present({len(next(n for n in nodes if n['label']==a).get('evidence',[]))} evidence)" for a in ALIASES),f'nodes={len(nodes)}')
 return 0
if __name__=='__main__': sys.exit(main())
