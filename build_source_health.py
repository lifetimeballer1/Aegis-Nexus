#!/usr/bin/env python3
"""Build honest per-source freshness, content and coverage telemetry."""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';STATUS=DATA/'live_status.json';OUT=DATA/'source_health.json'

def parse_dt(value):
 if not value:return None
 try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
 except Exception:return None

def age_minutes(value,now):
 dt=parse_dt(value)
 return round(max(0,(now-dt).total_seconds()/60),1) if dt else None

def registry():
 try:
  d=json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
  return d.get('feeds',[]) if isinstance(d.get('feeds'),list) else []
 except Exception:return []

def key(name,i):
 base=re.sub(r'[^a-z0-9]+','_',str(name).lower()).strip('_') or f'feed_{i}';return base

def main():
 now=datetime.now(timezone.utc);current=json.loads(STATUS.read_text(encoding='utf-8')) if STATUS.exists() else {};previous=json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
 previous_by={str(x.get('name')):x for x in previous.get('sources',[]) if isinstance(x,dict)};results={str(x.get('name')):x for x in current.get('sourceResults',[]) if isinstance(x,dict)}
 sources=[];seen=set()
 for i,item in enumerate(registry()):
  if not isinstance(item,dict) or not item.get('name'):continue
  name=str(item['name']);seen.add(name);r=results.get(name,{});old=previous_by.get(name,{})
  http_ok=bool(r.get('httpOk'));rows=int(r.get('rowsFetched',0) or 0);mode=str(r.get('mode') or 'not-polled');error=str(r.get('error') or '')
  coverage=list(r.get('coverage') or item.get('coverage') or [])
  category=str(r.get('category') or item.get('category') or item.get('type') or 'general')
  source_url=str(r.get('sourceUrl') or item.get('url') or '')
  if not http_ok:
   status='failed';content_status='unavailable';last_success=old.get('lastSuccess')
  elif rows>0:
   status='online';content_status='data_available';last_success=current.get('updatedAt') or now.isoformat()
  else:
   status='online';content_status='online_empty';last_success=current.get('updatedAt') or now.isoformat()
  if mode=='gdelt-domain-fallback':content_status='fallback_data_available'
  sources.append({'name':name,'url':source_url,'type':item.get('type','news'),'category':category,'coverage':coverage,'status':status,'contentStatus':content_status,'lastChecked':current.get('updatedAt') or now.isoformat(),'lastSuccess':last_success,'freshnessMinutes':age_minutes(last_success,now),'rowsFetched':rows,'newArticles':int(r.get('newArticles',0) or 0),'mode':mode,'consecutiveFailures':(int(old.get('consecutiveFailures',0) or 0)+1 if not http_ok else 0),'error':error,'fallbackAvailable':mode in {'online-empty','failed'} and not ('news.google.com' in source_url or 'gdeltproject.org' in source_url),'dataValue':'articles' if rows else 'none'})
 # X and any collector-only sources not represented in the registry
 for name,r in results.items():
  if name in seen:continue
  rows=int(r.get('rowsFetched',0) or 0);ok=bool(r.get('httpOk'));source_url=str(r.get('sourceUrl') or '')
  sources.append({'name':name,'url':source_url,'type':r.get('type','social'),'category':r.get('category','osint'),'coverage':list(r.get('coverage') or []),'status':'online' if ok else 'failed','contentStatus':'data_available' if rows else ('online_empty' if ok else 'unavailable'),'lastChecked':current.get('updatedAt') or now.isoformat(),'lastSuccess':current.get('updatedAt') if ok else None,'freshnessMinutes':age_minutes(current.get('updatedAt'),now) if ok else None,'rowsFetched':rows,'newArticles':int(r.get('newArticles',0) or 0),'mode':r.get('mode'),'consecutiveFailures':0 if ok else 1,'error':r.get('error',''),'fallbackAvailable':False,'dataValue':'posts' if rows else 'none'})
 online=sum(x['status']=='online' for x in sources);failed=sum(x['status']=='failed' for x in sources);empty=sum(x['contentStatus']=='online_empty' for x in sources);data=sum(x['contentStatus'] in {'data_available','fallback_data_available'} for x in sources);fallback=sum(x['contentStatus']=='fallback_data_available' for x in sources)
 coverage_counts={c:sum(c in x.get('coverage',[]) and x['contentStatus'] in {'data_available','fallback_data_available'} for x in sources) for c in ('united-states','china')}
 result={'version':3,'updatedAt':now.isoformat(),'collectorUpdatedAt':current.get('updatedAt'),'feedsChecked':len(sources),'rowsFetched':int(current.get('rowsFetched',0) or 0),'newArticles':int(current.get('newArticles',0) or 0),'databaseArticles':int(current.get('databaseArticles',0) or 0),'pollSeconds':int(current.get('pollSeconds',300) or 300),'summary':{'total':len(sources),'online':online,'failed':failed,'onlineWithData':data,'onlineEmpty':empty,'fallbackData':fallback,'dataCoveragePercent':round(100*data/len(sources),1) if sources else 0,'coverageSourcesWithData':coverage_counts},'sources':sources}
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result['summary'],ensure_ascii=False))
if __name__=='__main__':main()
