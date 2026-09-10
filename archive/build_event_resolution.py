#!/usr/bin/env python3
"""Resolve candidate duplicate live-event clusters with explainable signals."""
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent; EVENTS=ROOT/'data/live_events.json'; OUT=ROOT/'data/event_resolution.json'
STOP=set('the a an and or of to in on for with from after before as is are at by new latest report reports'.split())
def tokens(s): return {x for x in re.findall(r'[a-z0-9]{3,}',str(s or '').lower()) if x not in STOP}
def dt(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')) if v else None
 except:return None
def sim(a,b):
 ta,tb=tokens(a.get('title')),tokens(b.get('title')); j=len(ta&tb)/max(1,len(ta|tb)) if ta and tb else 0
 aa=set(a.get('anchors') or []); ab=set(b.get('anchors') or []); shared=aa&ab
 score=.60*j+min(.30,.15*len(shared))
 if a.get('category')==b.get('category'): score+=.08
 da,db=dt(a.get('lastSeen')),dt(b.get('lastSeen'))
 if da and db:
  mins=abs((da-db).total_seconds())/60
  if mins<=90: score+=.10
  elif mins<=240: score+=.05
 if not shared: score-=.10
 return max(0,min(1,score)),shared

def main():
 data=json.loads(EVENTS.read_text(encoding='utf-8')) if EVENTS.exists() else {'events':[]}; events=data.get('events',[])
 resolved=[]; used=set()
 for i,e in enumerate(events):
  if i in used: continue
  members=[e]; used.add(i); reasons=[]
  for j,x in enumerate(events[i+1:],i+1):
   if j in used: continue
   score,shared=sim(e,x)
   if score>=.60:
    members.append(x); used.add(j); reasons.append(f"score {score:.2f}; shared anchors: {', '.join(sorted(shared)) or 'none'}")
  domains=sorted({d for m in members for d in (m.get('sources') or [])})
  ids=[m.get('id') for m in members if m.get('id')]
  resolved.append({'resolution_id':f'ER-{len(resolved)+1:04d}','title':members[0].get('title'),'event_ids':ids,'report_count':sum(int(m.get('reportCount') or 0) for m in members),'unique_domains':domains,'member_count':len(members),'merge_reason':' ; '.join(reasons) if reasons else 'single candidate event cluster','confidence':'high' if len(members)>=3 and len(domains)>=3 else 'moderate' if len(members)>=2 else 'low'})
 out={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'generated_at':datetime.now(timezone.utc).isoformat(),'method':'event-cluster similarity using title tokens, geographic/actor anchors, category and publication timing; candidate grouping only','events':resolved}
 OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n'); print(f'resolved {len(resolved)} candidate groups from {len(events)} live clusters')
if __name__=='__main__': main()
