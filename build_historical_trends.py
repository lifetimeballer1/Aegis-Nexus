#!/usr/bin/env python3
"""Record the current tension sample, then build honest rolling trend summaries.

Promoted from archive/build_historical_trends.py (2026-09-14 stale-export
rewire). The archive version only re-rendered data/history.json, but NOTHING
in the refresh cycle appended to history.json — the last sample was days old,
so data/historical_trends.json (timeline tension context) rotted. This step
first appends one {updatedAt, tension, delta, scoreVersion} sample from the
fresh snapshot.json (capped, de-duplicated), then rebuilds the series, so the
trends export advances every cycle. No invented data: the sample is the live
snapshot tension, nothing else.

Safety: validate-then-swap (atomic tmp + os.replace on both files). Missing
snapshot tension is fatal — fail loud, never ship stale.
"""
from __future__ import annotations
import json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HISTORY_CAP=288
SERIES_CAP=240

def _paths(data_dir=None):
    data=Path(data_dir) if data_dir else ROOT/'data'
    return data/'snapshot.json',data/'history.json',data/'historical_trends.json'

def dt(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
 except:return None

def atomic_write(path,text):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(text,encoding='utf-8',newline='\n')
    os.replace(tmp,path)

def record_sample(history,snapshot,now):
    """Append one tension sample from the fresh snapshot. Returns new history list."""
    tension=snapshot.get('tension')
    if not isinstance(tension,(int,float)):
        raise ValueError('snapshot.json has no numeric tension — refusing to ship stale trends')
    score_version=snapshot.get('scoreVersion',5)
    rows=[x for x in history if isinstance(x,dict) and dt(x.get('updatedAt')) and isinstance(x.get('tension'),(int,float))]
    if rows:
        last=rows[-1]
        last_dt=dt(last['updatedAt'])
        # De-dupe: same tension re-stamped within 5 minutes adds no information.
        if last_dt and abs((now-last_dt).total_seconds())<300 and float(last['tension'])==float(tension):
            return rows
        delta=round(float(tension)-float(last['tension']),1)
    else:
        delta=0
    rows.append({'updatedAt':now.isoformat().replace('+00:00','Z'),'tension':tension,'delta':delta,'scoreVersion':score_version})
    rows.sort(key=lambda x:dt(x['updatedAt']))
    return rows[-HISTORY_CAP:]

def build_trends(rows,now):
    rows=sorted(rows,key=lambda x:dt(x['updatedAt']))
    latest=rows[-1] if rows else None
    out={'version':1,'updatedAt':now.isoformat().replace('+00:00','Z'),'availableSamples':len(rows),'availableHours':round((dt(rows[-1]['updatedAt'])-dt(rows[0]['updatedAt'])).total_seconds()/3600,1) if len(rows)>1 else 0,'series':rows[-SERIES_CAP:],'windows':{}}
    for name,hours in [('6h',6),('24h',24),('7d',168),('30d',720)]:
        if not latest:out['windows'][name]={'available':False,'reason':'No tension history yet'};continue
        start=now-timedelta(hours=hours);subset=[r for r in rows if dt(r['updatedAt'])>=start]
        if len(subset)<2:out['windows'][name]={'available':False,'reason':f'Only {len(subset)} samples in requested window'};continue
        first,last=subset[0],subset[-1];delta=round(float(last['tension'])-float(first['tension']),1);out['windows'][name]={'available':True,'samples':len(subset),'start':first['updatedAt'],'end':last['updatedAt'],'startTension':first['tension'],'endTension':last['tension'],'delta':delta,'trend':'UP' if delta>1 else 'DOWN' if delta<-1 else 'STABLE'}
    return out

def main(data_dir=None):
    snap_path,hist_path,out_path=_paths(data_dir)
    if not snap_path.is_file() or snap_path.stat().st_size==0:
        raise SystemExit('snapshot.json missing/empty — refusing to ship stale trends')
    snapshot=json.loads(snap_path.read_text(encoding='utf-8'))
    try: raw=json.loads(hist_path.read_text(encoding='utf-8')) if hist_path.exists() else []
    except Exception: raw=[]
    if not isinstance(raw,list): raw=[]
    now=datetime.now(timezone.utc)
    rows=record_sample(raw,snapshot,now)
    atomic_write(hist_path,json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    out=build_trends(rows,now)
    atomic_write(out_path,json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('HISTORICAL TRENDS:',{k:v.get('trend',v.get('reason')) for k,v in out['windows'].items()})
    return out

if __name__=='__main__': main()
