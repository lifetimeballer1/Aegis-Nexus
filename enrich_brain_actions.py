#!/usr/bin/env python3
"""Add source-backed action intelligence to the major U.S./China Brain hubs."""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';BRAIN=DATA/'intelligence_brain.json'
MAX_ACTION_EVIDENCE=100
ACTORS={
 'United States': [r'\bunited states\b',r'\bu\.s\.a?\.?\b',r'\busa\b',r'\bamerican\b',r'\bwashington\b',r'\bwhite house\b',r'\bpentagon\b'],
 'China': [r'\bchina\b',r'\bchinese\b',r'\bbeijing\b',r'\bpla\b',r'\bpeople.?s republic of china\b']
}
ACTION_TYPES={
 'military':['deploy','strike','attack','military','troops','forces','navy','aircraft','missile','exercise','drill','patrol','intercept','carrier','base','defense','defence'],
 'diplomatic':['meet','talks','diplomatic','ambassador','summit','negotiat','ally','alliance','agreement','treaty','envoy','recognize','recognise'],
 'economic':['tariff','trade','export','import','sanction','investment','ban','restriction','customs','subsid','stimulus','interest rate','currency','debt'],
 'technology':['chip','semiconductor','technology','ai','artificial intelligence','export control','quantum','telecom','5g','6g','rare earth'],
 'security':['sanction','security','intelligence','cyber','espionage','counterterror','counter-terror','law enforcement','border'],
 'political':['election','president','congress','parliament','policy','legislation','bill','executive order','government','political'],
 'maritime':['naval','ship','vessel','coast guard','south china sea','taiwan strait','freedom of navigation','maritime'],
 'energy':['oil','gas','lng','energy','nuclear','uranium','pipeline','opec','electricity']
}

def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def text(r):
 return ' '.join(str(r.get(k,'')) for k in ('title','headline','summary','description','content','detail','claim','assessment','text','actor','actors','organization','organizations','country','location','category','type','tags','keywords','eventType')).lower()
def evidence(r):
 if not isinstance(r,dict):return None
 title=str(r.get('title') or r.get('name') or r.get('headline') or r.get('label') or r.get('description') or '').strip()
 url=str(r.get('original_link') or r.get('url') or r.get('sourceUrl') or r.get('source_url') or r.get('link') or '').strip()
 source=str(r.get('sourceLabel') or r.get('source') or r.get('publisher') or r.get('provider') or '').strip()
 if not title or not (url or source):return None
 return {'title':title[:300],'url':url,'source':source or 'Public source','time':str(r.get('publishedAt') or r.get('published_date') or r.get('updatedAt') or r.get('time') or '')}
def key(e):return (e['title'].lower(),e['url'].lower(),e['source'].lower())
def main():
 brain=json.loads(BRAIN.read_text(encoding='utf-8'))
 records=[]
 for fn in ('live_articles.json','breaking_news.json','event_intelligence.json','claims.json','intelligence_assessment.json','what_changed.json','intelligence_graph.json','snapshot.json'):
  p=DATA/fn
  if p.exists():
   try:records += list(walk(json.loads(p.read_text(encoding='utf-8'))))
   except Exception:pass
 by={str(n.get('label')):n for n in brain.get('nodes',[])}
 for actor,patterns in ACTORS.items():
  node=by.get(actor)
  if not node:continue
  actions={k:[] for k in ACTION_TYPES}; seen=set(); targets={}
  for r in records:
   t=text(r)
   if not any(re.search(p,t) for p in patterns):continue
   ev=evidence(r)
   if not ev:continue
   ek=key(ev)
   if ek in seen:continue
   seen.add(ek)
   matched=[k for k,terms in ACTION_TYPES.items() if any(term in t for term in terms)]
   if not matched:continue
   for kind in matched:
    if len(actions[kind])<MAX_ACTION_EVIDENCE:actions[kind].append(ev)
   # Identify explicit major counterpart/target mentions without inventing causality.
   for target in by:
    if target!=actor and re.search(r'(?<![a-z])'+re.escape(target.lower())+r'(?![a-z])',t):
     targets[target]=targets.get(target,0)+1
  node['actions']={k:v for k,v in actions.items() if v}
  node['actionCounts']={k:len(v) for k,v in actions.items() if v}
  node['actionEvidenceCount']=sum(len(v) for v in actions.values())
  node['actionTargets']=sorted([{'target':k,'coMentions':v} for k,v in targets.items()],key=lambda x:x['coMentions'],reverse=True)[:20]
  node['actionIntelligence']={'method':'Source-backed classification of records mentioning the actor using explicit action vocabulary. Counts are evidence volumes, not measures of intent or impact.','updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
 brain['actionLayer']={'version':1,'actors':['United States','China'],'sourceBackedOnly':True,'categories':list(ACTION_TYPES),'description':'Action evidence is attached to the U.S. and China major hubs so the Intelligence Web can distinguish activity from simple country mentions.','updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
 brain['updatedAt']=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
 BRAIN.write_text(json.dumps(brain,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
 print('BRAIN ACTION LAYER:',[(a,by.get(a,{}).get('actionEvidenceCount',0)) for a in ACTORS])
if __name__=='__main__':main()
