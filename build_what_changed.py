#!/usr/bin/env python3
"""Build a compact, event-aware 'what changed' feed from public artifacts."""
from __future__ import annotations
import json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
DATA=Path(__file__).resolve().parent/'data'

def load(name,default):
 try:return json.loads((DATA/name).read_text(encoding='utf-8'))
 except Exception:return default

def parse(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
 except Exception:return None

def main():
 now=datetime.now(timezone.utc); assessment=load('intelligence_assessment.json',{}); events=load('live_events.json',{}); previous=load('what_changed.json',{}); old_ids={str(x.get('eventId')) for x in previous.get('items',[]) if x.get('eventId')}
 items=[]
 for x in assessment.get('whatChanged',[])[:20]:
  if not isinstance(x,dict):continue
  delta=float(x.get('delta',0) or 0)
  if abs(delta)>=3:items.append({'type':'indicator','entity':x.get('entity'),'title':f"{x.get('entity')} indicator moved {'up' if delta>0 else 'down'}",'detail':f"Score {x.get('score',0)}/100 · {x.get('level','WATCH')} · {x.get('evidenceCount',0)} matching reports",'delta':delta,'score':x.get('score',0),'level':x.get('level','WATCH')})
 for e in events.get('events',[])[:50]:
  if not isinstance(e,dict):continue
  t=parse(e.get('firstSeen') or e.get('lastSeen'))
  if not t or now-t>timedelta(hours=12):continue
  eid=str(e.get('id') or '')
  items.append({'type':'event','eventId':eid,'entity':None,'title':e.get('title','New live event'),'detail':f"{e.get('reportCount',0)} reports · {e.get('sourceCount',0)} source domains · {str(e.get('confidence','unknown')).upper()} confidence",'delta':0,'score':None,'level':str(e.get('confidence','unknown')).upper(),'new':eid not in old_ids,'time':t.isoformat()})
 rank={'event':2,'indicator':1};items.sort(key=lambda x:(int(x.get('new',False)),rank.get(x.get('type'),0),abs(float(x.get('delta',0) or 0)),str(x.get('time',''))),reverse=True)
 out={'version':1,'updatedAt':now.isoformat().replace('+00:00','Z'),'window':'12 hours','items':items[:20],'summary':{'newEvents':sum(1 for x in items if x.get('type')=='event' and x.get('new')),'indicatorMoves':sum(1 for x in items if x.get('type')=='indicator'),'total':min(20,len(items))}}
 (DATA/'what_changed.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print('WHAT CHANGED:',out['summary'])
if __name__=='__main__':main()
