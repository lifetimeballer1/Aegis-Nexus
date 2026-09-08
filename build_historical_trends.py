#!/usr/bin/env python3
"""Build honest rolling trend summaries from the retained tension history."""
from __future__ import annotations
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
DATA=Path(__file__).resolve().parent/'data'
def dt(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
 except:return None
def main():
 try:raw=json.loads((DATA/'history.json').read_text(encoding='utf-8'))
 except:raw=[]
 rows=[x for x in raw if isinstance(x,dict) and dt(x.get('updatedAt')) and isinstance(x.get('tension'),(int,float))];rows.sort(key=lambda x:dt(x['updatedAt']))
 now=datetime.now(timezone.utc);latest=rows[-1] if rows else None;out={'version':1,'updatedAt':now.isoformat().replace('+00:00','Z'),'availableSamples':len(rows),'availableHours':round((dt(rows[-1]['updatedAt'])-dt(rows[0]['updatedAt'])).total_seconds()/3600,1) if len(rows)>1 else 0,'series':rows[-240:],'windows':{}}
 for name,hours in [('6h',6),('24h',24),('7d',168),('30d',720)]:
  if not latest:out['windows'][name]={'available':False,'reason':'No tension history yet'};continue
  start=now-timedelta(hours=hours);subset=[r for r in rows if dt(r['updatedAt'])>=start]
  if len(subset)<2:out['windows'][name]={'available':False,'reason':f'Only {len(subset)} samples in requested window'};continue
  first,last=subset[0],subset[-1];delta=round(float(last['tension'])-float(first['tension']),1);out['windows'][name]={'available':True,'samples':len(subset),'start':first['updatedAt'],'end':last['updatedAt'],'startTension':first['tension'],'endTension':last['tension'],'delta':delta,'trend':'UP' if delta>1 else 'DOWN' if delta<-1 else 'STABLE'}
 (DATA/'historical_trends.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('HISTORICAL TRENDS:',{k:v.get('trend',v.get('reason')) for k,v in out['windows'].items()})
if __name__=='__main__':main()
