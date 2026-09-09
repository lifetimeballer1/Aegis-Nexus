#!/usr/bin/env python3
"""Fetch a keyless near-real-time breaking-news layer from GDELT and merge it into the snapshot.

The discovery layer deliberately includes dedicated U.S. and China coverage so the
strategic actors that drive a large share of global security, trade, technology,
and diplomatic activity cannot disappear behind generic conflict queries.
"""
from __future__ import annotations
import json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';SNAP=DATA/'snapshot.json';OUT=DATA/'breaking_news.json'
QUERIES=[
 '(Russia OR Ukraine OR NATO OR missile OR airstrike OR bombing OR explosion OR invasion OR attack OR ceasefire OR coup OR "armed conflict")',
 '(earthquake OR tsunami OR hurricane OR wildfire OR flood OR volcano OR "mass casualty")',
 '(oil OR tanker OR "Strait of Hormuz" OR sanctions OR tariff OR "market crash" OR "central bank")',
 '(Iran OR Israel OR Gaza OR Yemen OR Sudan OR "Democratic Republic of Congo" OR Somalia OR Sahel OR Mexico OR cartel)',
 '("United States" OR "U.S." OR America OR American OR Washington OR "White House" OR Pentagon OR Congress OR NATO) (policy OR military OR defense OR diplomacy OR sanctions OR tariff OR trade OR technology OR semiconductor OR election OR security OR treaty)',
 '(China OR Chinese OR Beijing OR "People\'s Liberation Army" OR PLA OR Xi) (military OR defense OR diplomacy OR Taiwan OR trade OR tariff OR semiconductor OR technology OR economy OR sanctions OR South China Sea OR shipping OR investment)'
]
def clean(s):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',str(s or ''))).strip()[:900]
def fetch(q):
 u='https://api.gdeltproject.org/api/v2/doc/doc?query='+quote(q)+'&mode=artlist&format=rss&maxrecords=75&timespan=15min&sort=datedesc';req=Request(u,headers={'User-Agent':'AegisNexus/13.0','Accept':'application/rss+xml, application/xml'})
 with urlopen(req,timeout=10) as r:root=ET.fromstring(r.read())
 rows=[]
 for item in root.findall('.//item')[:75]:
  title=clean(item.findtext('title'));link=clean(item.findtext('link'));pub=clean(item.findtext('pubDate'));desc=clean(item.findtext('description'))
  if link and title:rows.append({'title':title,'url':link,'published_date':pub,'summary':desc,'source':'GDELT near-real-time discovery','sourceType':'open-data','priority':'breaking'})
 return rows
def main():
 rows=[];errors=[];seen=set()
 with ThreadPoolExecutor(max_workers=6) as pool:
  futures=[pool.submit(fetch,q) for q in QUERIES]
  for f in as_completed(futures):
   try:
    for r in f.result():
     if r['url'] not in seen:seen.add(r['url']);rows.append(r)
   except Exception as e:errors.append(f'{type(e).__name__}: {e}'[:180])
 rows=rows[:250];payload={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'window':'15min','provider':'GDELT DOC 2.0','sourceType':'open-data','articles':rows,'errors':errors};DATA.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 if SNAP.exists():
  data=json.loads(SNAP.read_text(encoding='utf-8'));stories=data.get('stories',[]) if isinstance(data.get('stories'),list) else [];existing={str(x.get('url') or x.get('link') or '') for x in stories if isinstance(x,dict)};additions=[]
  for r in rows:
   if r['url'] not in existing:additions.append({'title':r['title'],'url':r['url'],'publishedAt':r['published_date'],'published_date':r['published_date'],'summary':r['summary'],'description':r['summary'],'source':r['source'],'sourceLabel':r['source'],'category':'breaking','priority':'breaking','sourceType':'open-data'})
  data['stories']=(additions+stories)[:2000];data['breakingNews']=payload;data['updatedAt']=payload['updatedAt'];SNAP.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(f'BREAKING INTEL: {len(rows)} discoveries; {len(errors)} query errors')
if __name__=='__main__':main()
