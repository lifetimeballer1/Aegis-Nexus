#!/usr/bin/env python3
"""Maintain a compact historical timeline for resolved live events.
No API key required. Uses the current live-event snapshot and preserves only
structured observations so the UI can explain how an event developed over time.
"""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
LIVE=DATA/'live_events.json'
OUT=DATA/'event_history.json'

def clean(v): return re.sub(r'\s+',' ',str(v or '')).strip()
def tokens(v): return set(re.findall(r'[a-z0-9]{4,}',clean(v).lower()))
def fingerprint(e):
    anchors='|'.join(sorted(str(x).lower() for x in (e.get('anchors') or [])))
    category=str(e.get('category','general')).lower()
    # Use anchors/category as the primary identity. If anchors are absent, use a
    # compact normalized title signature; this avoids creating a new history key
    # for every headline punctuation/word-order change.
    if anchors:
        return hashlib.sha1((anchors+'::'+category).encode()).hexdigest()[:20]
    words=sorted(tokens(e.get('title','')))
    return hashlib.sha1(('::'.join(words[:12])+'::'+category).encode()).hexdigest()[:20]
def iso(v):
    if not v: return None
    try:
        d=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    except Exception: return None

def main():
    if not LIVE.exists(): raise SystemExit('live_events.json missing')
    live=json.loads(LIVE.read_text(encoding='utf-8'))
    now=datetime.now(timezone.utc)
    try: previous=json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    except Exception: previous={}
    histories=previous.get('events',{}) if isinstance(previous,dict) else {}
    for e in live.get('events',[])[:80]:
        fid=fingerprint(e)
        h=histories.get(fid,{'id':fid,'title':e.get('title',''),'category':e.get('category','general'),'anchors':e.get('anchors',[]),'observations':[]})
        h['title']=e.get('title') or h.get('title')
        h['category']=e.get('category') or h.get('category')
        h['anchors']=sorted(set((h.get('anchors') or [])+(e.get('anchors') or [])))[:16]
        observation={'observedAt':now.isoformat().replace('+00:00','Z'),'firstSeen':iso(e.get('firstSeen')),'lastSeen':iso(e.get('lastSeen')),'reportCount':int(e.get('reportCount') or 0),'sourceCount':int(e.get('sourceCount') or 0),'confidence':e.get('confidence','unknown'),'title':e.get('title',''),'urls':(e.get('urls') or [])[:5]}
        obs=h.setdefault('observations',[])
        sig=(observation['reportCount'],observation['sourceCount'],observation['confidence'],observation['title'])
        prev_sig=None
        if obs:
            last=obs[-1]; prev_sig=(int(last.get('reportCount') or 0),int(last.get('sourceCount') or 0),last.get('confidence','unknown'),last.get('title',''))
        if prev_sig != sig: obs.append(observation)
        cutoff=now-timedelta(days=30)
        kept=[]
        for o in obs[-240:]:
            try:
                if datetime.fromisoformat(o['observedAt'].replace('Z','+00:00'))>=cutoff: kept.append(o)
            except Exception: pass
        h['observations']=kept[-180:]
        histories[fid]=h
    active={}
    for k,h in histories.items():
        obs=h.get('observations') or []
        if obs:
            try:
                dt=datetime.fromisoformat(obs[-1]['observedAt'].replace('Z','+00:00'))
                if now-dt<=timedelta(days=30): active[k]=h
            except Exception: pass
    payload={'updatedAt':now.isoformat().replace('+00:00','Z'),'window':'30 days','method':'stable candidate fingerprint plus material observation snapshots; historical records are descriptive, not proof of event identity','events':active}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'EVENT HISTORY: {len(active)} tracked events')
if __name__=='__main__': main()
