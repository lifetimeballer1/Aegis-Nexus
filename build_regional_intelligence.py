#!/usr/bin/env python3
"""Build compact regional intelligence summaries from current public signals."""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
DATA=Path(__file__).resolve().parent/'data'
REGIONS={'North America':r'canada|united states|america|mexico|greenland|caribbean','South America':r'brazil|argentina|colombia|venezuela|peru|chile|ecuador|bolivia|paraguay|uruguay|guyana|suriname','Europe':r'ukraine|russia|united kingdom|britain|france|germany|poland|belarus|baltic|europe|nato','Middle East':r'iran|iraq|israel|gaza|palestine|syria|lebanon|yemen|jordan|saudi|qatar|uae|hormuz|red sea','Africa':r'sudan|south sudan|somalia|ethiopia|eritrea|kenya|nigeria|niger|mali|burkina|chad|congo|drc|sahel|libya|egypt|mozambique|rwanda|uganda|tanzania|cameroon','South Asia':r'india|pakistan|afghanistan|bangladesh|nepal|sri lanka','East Asia':r'china|taiwan|japan|south korea|north korea','Southeast Asia':r'myanmar|thailand|vietnam|philippines|indonesia|malaysia','Oceania':r'australia|new zealand|pacific islands'}

def load(name,default):
 try:return json.loads((DATA/name).read_text(encoding='utf-8'))
 except Exception:return default

def region(text):
 low=str(text or '').lower();hits=[r for r,p in REGIONS.items() if re.search(p,low)]
 return hits[0] if hits else 'Other'

def main():
 snap=load('snapshot.json',{});events=load('live_events.json',{});old=load('regional_intelligence.json',{});old_counts={r:x.get('reports',0) for r,x in old.get('regions',{}).items()}
 rows={r:{'reports':0,'active24h':0,'events':0,'conflictReports':0,'topStories':[]} for r in REGIONS}
 for s in snap.get('stories',[]):
  if not isinstance(s,dict):continue
  rg=region((s.get('title','')+' '+s.get('summary',''))); 
  if rg not in rows:continue
  rows[rg]['reports']+=1
  t=str(s.get('time') or s.get('published_date') or s.get('publishedAt') or '')
  try:
   age=(datetime.now(timezone.utc)-datetime.fromisoformat(t.replace('Z','+00:00')).astimezone(timezone.utc)).total_seconds()/3600
   if age<=24:rows[rg]['active24h']+=1
  except Exception:pass
  if re.search(r'war|attack|strike|missile|drone|airstrike|troops|military|fighting|coup|clash',str(s.get('title','')),re.I):rows[rg]['conflictReports']+=1
  if len(rows[rg]['topStories'])<3:rows[rg]['topStories'].append({'title':s.get('title'),'url':s.get('source') or s.get('url')})
 for e in events.get('events',[]):
  if not isinstance(e,dict):continue
  rg=region(e.get('title',''))
  if rg in rows:rows[rg]['events']+=1
 for r,v in rows.items():
  v['deltaReports']=v['reports']-int(old_counts.get(r,0) or 0)
  v['trend']='UP' if v['deltaReports']>0 else 'DOWN' if v['deltaReports']<0 else 'STABLE'
 ranked=sorted(rows.items(),key=lambda x:(x[1]['active24h'],x[1]['conflictReports'],x[1]['events']),reverse=True)
 out={'version':1,'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'method':'Rule-based regional classification from current public-report titles, summaries and live-event titles.','regions':rows,'priorityOrder':[r for r,_ in ranked]}
 (DATA/'regional_intelligence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print('REGIONAL INTELLIGENCE:',[(r,v['active24h'],v['conflictReports']) for r,v in ranked])
if __name__=='__main__':main()
