#!/usr/bin/env python3
"""Maintain a compact historical timeline for resolved live events.
No API key required. Uses the current live-event snapshot and preserves only
structured observations so the UI can explain how an event developed over time.

Promoted from archive/build_event_history.py (2026-09-14 stale-export rewire):
the canonical refresh regenerates live_events.json every cycle, and this step
appends fresh observations so data/event_history.json can never rot again.
Reader contract (js/modules/timeline.js) unchanged: {updatedAt, events: {id:
{observations: [{observedAt, ...}]}}}.

Safety: validate inputs, build fully in memory, atomic swap (tmp + os.replace)
so a crash can never leave a partial file. Missing/empty live_events.json is
fatal — the pipeline must fail loud, never silently ship a stale timeline.
"""
from __future__ import annotations
import hashlib,json,os,re
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WINDOW_DAYS=30
MAX_EVENTS_PER_RUN=80
MAX_OBS_PER_EVENT=180

def _paths(data_dir=None):
    data=Path(data_dir) if data_dir else ROOT/'data'
    return data/'live_events.json',data/'event_history.json'

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

def build(live_events):
    """Pure transform: (live payload, previous histories) -> new payload. No I/O."""
    now=datetime.now(timezone.utc)
    histories=dict(live_events.get('_previous',{}))
    for e in live_events.get('events',[])[:MAX_EVENTS_PER_RUN]:
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
        cutoff=now-timedelta(days=WINDOW_DAYS)
        kept=[]
        for o in obs[-240:]:
            try:
                if datetime.fromisoformat(o['observedAt'].replace('Z','+00:00'))>=cutoff: kept.append(o)
            except Exception: pass
        h['observations']=kept[-MAX_OBS_PER_EVENT:]
        histories[fid]=h
    active={}
    for k,h in histories.items():
        obs=h.get('observations') or []
        if obs:
            try:
                dt=datetime.fromisoformat(obs[-1]['observedAt'].replace('Z','+00:00'))
                if now-dt<=timedelta(days=WINDOW_DAYS): active[k]=h
            except Exception: pass
    return {'updatedAt':now.isoformat().replace('+00:00','Z'),'window':'30 days','method':'stable candidate fingerprint plus material observation snapshots; historical records are descriptive, not proof of event identity','events':active}

def atomic_write(path,text):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(text,encoding='utf-8',newline='\n')
    os.replace(tmp,path)

def main(data_dir=None):
    live_path,out_path=_paths(data_dir)
    if not live_path.is_file() or live_path.stat().st_size==0:
        raise SystemExit('live_events.json missing/empty — refusing to ship a stale timeline')
    live=json.loads(live_path.read_text(encoding='utf-8'))
    if not isinstance(live,dict) or not isinstance(live.get('events'),list) or not live['events']:
        raise SystemExit('live_events.json has no events — refusing to ship a stale timeline')
    try: previous=json.loads(out_path.read_text(encoding='utf-8')) if out_path.exists() else {}
    except Exception: previous={}
    live['_previous']=previous.get('events',{}) if isinstance(previous,dict) else {}
    payload=build(live)
    if not payload['events']:
        raise SystemExit('event-history build produced zero events — refusing to overwrite')
    atomic_write(out_path,json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(f"EVENT HISTORY: {len(payload['events'])} tracked events")
    return payload

if __name__=='__main__': main()
