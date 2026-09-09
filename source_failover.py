#!/usr/bin/env python3
"""Replace failed news feeds with public no-key fallback feeds and publish health state.

Quarantine map (verified live 2026-09-09, re-verify when a replacement is attempted):
- France 24 RSS (https://www.france24.com/en/rss): endpoint serves an HTML page,
  not RSS. REPLACED in the canonical catalog by RFI World
  (https://www.rfi.fr/en/general/rss, France Medias Monde sister outlet).
- X account proxies (rss.xcancel.com / xcancel.com): all five handles answer with
  a proxy challenge/whitelist response. QUARANTINED — no working no-key RSS
  proxy known; recorded honestly as failed and tolerated by the source health
  gate (optional social feeds must not block publication).
- NPR topic feeds (feeds.npr.org): valid IDs intermittently answer HTTP 404.
  NOT quarantined — covered by collector retry (news_feed_db.FETCH_RETRIES).
- GDELT Doc API (api.gdeltproject.org): bursts answer HTTP 429. NOT
  quarantined — covered by collector GDELT spacing (>=2.5s) plus 429/5xx
  backoff; CURRENT_FALLBACKS below keeps a Google News path ready when a
  GDELT mirror itself is the failing source.
"""
from __future__ import annotations
import html,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request,urlopen
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';SNAP=DATA/'snapshot.json';SOURCES=DATA/'sources.json';STATUS=DATA/'live_status.json';UA='Mozilla/5.0 (compatible; GlobalPulse/3.0)'
FALLBACKS={'GDELT Climate & Disaster Watch':'climate disaster flood wildfire drought famine epidemic','GDELT Climate Security Watch':'climate security migration food water disease crisis','GDELT Live — U.S. Politics':'US politics Congress White House election Senate','CNN Politics — GDELT Mirror':'CNN politics Trump Congress Senate White House','Axios Politics — GDELT Mirror':'Axios politics Trump Congress Senate White House','Morse Report — GDELT Mirror':'Morse Report politics Congress Senate White House','GDELT Live — Global Economics':'global economy markets oil inflation trade central bank','GDELT Live — World Politics':'world politics diplomacy sanctions election conflict','GDELT Live — Global':'world conflict war military crisis sanctions','GDELT Live — Africa':'Africa conflict war military Sudan Congo Sahel Nigeria Somalia','GDELT Live — Americas':'South America conflict Colombia Venezuela Brazil Ecuador Peru Haiti Mexico','GDELT Live — Middle East':'Middle East conflict Iran Israel Gaza Yemen Syria Iraq','FAO GIEWS':'FAO food security famine drought crop harvest Africa','ReliefWeb':'humanitarian crisis conflict disaster Africa Asia Middle East'}
# Fallbacks keyed to CURRENT canonical catalog/collector names so the loop below
# actually triggers for presently observed failures (legacy FALLBACKS keys above
# predate the catalog and would otherwise never match a live failedSource).
CURRENT_FALLBACKS={'SOUTHCOM Official Reporting — GDELT Mirror':'SOUTHCOM US Southern Command military Caribbean','GDELT — Western Hemisphere Counter-Cartel':'cartel narco-terrorism Caribbean Eastern Pacific'}
# Dead endpoints with documented outcomes. 'replaced' => catalog already carries
# the successor (record a doc entry, no fetch). 'unavailable' => no working
# no-key path known (record honestly, no fetch, health thresholds tolerate).
QUARANTINE={'France 24':{'status':'replaced','replacement':'RFI World','replacementUrl':'https://www.rfi.fr/en/general/rss','note':'France 24 /en/rss serves HTML, not RSS (verified 2026-09-09); catalog now polls RFI World instead.'},'X @NASA':{'status':'unavailable','note':'X proxy challenge/whitelist; no working no-key RSS proxy known (verified 2026-09-09).'},'X @WhiteHouse':{'status':'unavailable','note':'X proxy challenge/whitelist; no working no-key RSS proxy known (verified 2026-09-09).'},'X @POTUS':{'status':'unavailable','note':'X proxy challenge/whitelist; no working no-key RSS proxy known (verified 2026-09-09).'},'X @NATO':{'status':'unavailable','note':'X proxy challenge/whitelist; no working no-key RSS proxy known (verified 2026-09-09).'},'X @UN':{'status':'unavailable','note':'X proxy challenge/whitelist; no working no-key RSS proxy known (verified 2026-09-09).'}}
def now():return datetime.now(timezone.utc).isoformat()
def clean(text):return re.sub(r'\s+',' ',html.unescape(text or '')).strip()
def fetch(query):
 url='https://news.google.com/rss/search?q='+quote_plus(query)+'&hl=en-US&gl=US&ceid=US:en';req=Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/xml'})
 with urlopen(req,timeout=15) as r:root=ET.fromstring(r.read())
 return [{'title':clean(i.findtext('title')),'url':clean(i.findtext('link')),'source':clean(i.find('source').text if i.find('source') is not None else 'Google News'),'published_date':clean(i.findtext('pubDate'))} for i in root.findall('./channel/item') if clean(i.findtext('title')) and clean(i.findtext('link'))][:30]
def story_key(item):
 return str(item.get('url') or '').strip() or f"title:{str(item.get('title') or '').strip().lower()}|time:{str(item.get('published_date') or item.get('time') or '').strip()}"
def merge_stories(existing, additions):
 merged=[];seen=set()
 for item in list(existing or [])+list(additions or []):
  if not isinstance(item,dict):continue
  key=story_key(item)
  if not key or key in seen:continue
  seen.add(key);merged.append(item)
 return merged
def main():
 data=json.loads(SNAP.read_text(encoding='utf-8')) if SNAP.exists() else {};sources=json.loads(SOURCES.read_text(encoding='utf-8')) if SOURCES.exists() else {};live=json.loads(STATUS.read_text(encoding='utf-8')) if STATUS.exists() else {};failed_sources={str(x.get('source') if isinstance(x,dict) else x) for x in (live.get('failedSources') or [])};feeds=sources.get('feeds',[]);total=int(live.get('feedsChecked') or len(feeds));stories=list(data.get('stories',[]));existing={story_key(x) for x in stories if isinstance(x,dict)};additions=[];replacements=[]
 for name,query in list(FALLBACKS.items())+[(k,v) for k,v in CURRENT_FALLBACKS.items() if k not in FALLBACKS]:
  if failed_sources and name not in failed_sources:continue
  if not failed_sources and not any(name==f.get('name') for f in feeds):continue
  try:
   rows=fetch(query);added=0
   for row in rows:
    if story_key(row) in existing:continue
    additions.append({'title':row['title'],'url':row['url'],'published_date':row['published_date'],'time':row['published_date'],'summary_snippet':'Fallback discovery via Google News RSS; publisher: '+row['source'],'summary':'Fallback discovery via Google News RSS; publisher: '+row['source'],'source':row['source'],'sourceLabel':row['source'],'sourceType':'fallback-news','fallbackFor':name,'credit_metadata':'Google News RSS fallback'});existing.add(story_key(row));added+=1
   replacements.append({'failedSource':name,'fallback':'Google News RSS','query':query,'storiesAdded':added,'checkedAt':now()})
  except Exception as exc:replacements.append({'failedSource':name,'fallback':'Google News RSS','query':query,'storiesAdded':0,'error':f'{type(exc).__name__}: {exc}'[:160],'checkedAt':now()})
 for name in sorted(failed_sources):
  info=QUARANTINE.get(name)
  if info and not any(r.get('failedSource')==name for r in replacements):
   replacements.append({'failedSource':name,'fallback':info.get('replacement') or 'none available','query':'','storiesAdded':0,'quarantine':info.get('status'),'note':info.get('note'),'checkedAt':now()})
 fallback_count=sum(1 for x in replacements if x.get('storiesAdded',0)>0);down=len(failed_sources) if failed_sources else sum(1 for x in replacements if x.get('error'));data['stories']=merge_stories(stories,additions);data['sourceFailover']={'updatedAt':now(),'replacements':replacements};data['failoverState']={'updatedAt':now(),'total':total,'down':down,'healthy':max(0,total-down),'fallbacks':fallback_count,'failedSources':sorted(failed_sources)};data['updatedAt']=now();SNAP.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print('SOURCE FAILOVER:',json.dumps(data['failoverState'],ensure_ascii=False));print('STORY PRESERVATION:',len(stories),'existing +',len(additions),'fallback =',len(data['stories']))
if __name__=='__main__':main()
