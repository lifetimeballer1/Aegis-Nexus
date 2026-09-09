#!/usr/bin/env python3
"""Cluster recent public reports into explainable live events.
No API key required; consumes the existing snapshot and rapid open-data layer.
"""
from __future__ import annotations
import json,re,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; SNAP=DATA/'snapshot.json'; RAPID=DATA/'breaking_news.json'; OUT=DATA/'live_events.json'
STOP=set('the a an and or of to in on for from with by as at is are was were has have had this that report reports reported says said after before over into near amid during its their his her'.split())
KEYWORDS={'conflict':{'attack','airstrike','missile','bomb','bombing','strike','war','fighting','invasion','clash','military','troops'},'diplomatic':{'nato','ceasefire','talks','summit','diplomatic','sanction','sanctions','agreement','negotiation'},'economic':{'tariff','trade','inflation','market','stocks','oil','crude','shipping','supply','economy','rate'},'disaster':{'earthquake','tsunami','hurricane','wildfire','flood','volcano','storm'},'political':{'election','president','parliament','congress','coup','government'}}
# High-value geographic anchors. This is deliberately conservative and explainable.
ANCHORS={'iran','israel','russia','ukraine','china','taiwan','sudan','somalia','nigeria','niger','mali','burkina','congo','drc','ethiopia','egypt','yemen','lebanon','syria','iraq','gaza','hamas','hezbollah','nato','sahel','horn','hormuz','red sea','black sea','persian gulf','uk','britain','france','germany','united states','america','mexico','venezuela','haiti','colombia'}
def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def tokens(s): return {x for x in re.findall(r'[a-z0-9]{4,}',clean(s).lower()) if x not in STOP}
def anchors(s):
 t=clean(s).lower(); return {a for a in ANCHORS if a in t}
def kind(text):
 t=tokens(text); scores={k:len(t&v) for k,v in KEYWORDS.items()}; return max(scores,key=scores.get) if max(scores.values(),default=0) else 'general'
def source_domain(url):
 try:return urlparse(url).netloc.lower().removeprefix('www.')
 except:return ''
def parse_time(r):
 for k in ('publishedAt','published_at','published_date','time','date'):
  v=r.get(k)
  if not v: continue
  try:return datetime.fromisoformat(str(v).replace('Z','+00:00'))
  except: pass
 return None
def similarity(r,c):
 title=clean(r.get('title') or r.get('name')); ts=tokens(title); aa=anchors(title)
 if not ts:return 0
 j=len(ts & c['tokens'])/max(1,len(ts|c['tokens']))
 ca=aa & c['anchors']; score=j*.60 + min(.28,.14*len(ca))
 if kind(title)==c['kind']: score+=.08
 rt=parse_time(r); ct=c.get('latest_time')
 if rt and ct:
  mins=abs((rt-ct).total_seconds())/60
  if mins<=90: score+=.10
  elif mins<=240: score+=.05
 # Without a shared geographic/actor anchor, require stronger title similarity.
 if not ca: score-=.10
 return max(0,min(1,score))
def main():
 stories=[]
 if SNAP.exists():
  d=json.loads(SNAP.read_text(encoding='utf-8')); stories += [x for x in d.get('stories',[]) if isinstance(x,dict)][:800]
 if RAPID.exists():
  d=json.loads(RAPID.read_text(encoding='utf-8')); stories += [x for x in d.get('articles',[]) if isinstance(x,dict)][:150]
 unique={}
 for r in stories:
  title=clean(r.get('title') or r.get('name')); url=clean(r.get('original_link') or r.get('url') or r.get('link'))
  if not title: continue
  key=url or hashlib.sha1(title.lower().encode()).hexdigest(); unique[key]=r
 reports=list(unique.values()); reports.sort(key=lambda r:parse_time(r) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)
 clusters=[]
 for r in reports:
  title=clean(r.get('title') or r.get('name')); ts=tokens(title); aa=anchors(title); placed=False
  best=None; best_score=0
  for c in clusters:
   score=similarity(r,c)
   if score>=.58 and score>best_score: best,best_score=c,score
  if best is not None:
   best['reports'].append(r); best['tokens'] |= ts; best['anchors'] |= aa; best['latest_time']=max([best.get('latest_time'),parse_time(r)] if best.get('latest_time') and parse_time(r) else [x for x in [best.get('latest_time'),parse_time(r)] if x],default=None); placed=True
  if not placed:
   clusters.append({'tokens':ts,'anchors':aa,'kind':kind(title),'reports':[r],'latest_time':parse_time(r)})
 events=[]
 for c in clusters:
  rs=c['reports']; rs.sort(key=lambda x:parse_time(x) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)
  lead=clean(rs[0].get('title') or rs[0].get('name')); domains=[]; links=[]; seen=set()
  for r in rs:
   u=clean(r.get('original_link') or r.get('url') or r.get('link')); dom=source_domain(u)
   if dom and dom not in domains: domains.append(dom)
   if u and u not in seen: seen.add(u); links.append(u)
  confidence='high' if len(domains)>=3 else 'moderate' if len(domains)>=2 else 'low'
  events.append({'id':hashlib.sha1((lead.lower()+c['kind']).encode()).hexdigest()[:16],'title':lead,'category':c['kind'],'confidence':confidence,'reportCount':len(rs),'sourceCount':len(domains),'sources':domains[:8],'anchors':sorted(c['anchors'])[:12],'firstSeen':min([str(x.get('publishedAt') or x.get('published_date') or '') for x in rs if x.get('publishedAt') or x.get('published_date')] or ['']),'lastSeen':max([str(x.get('publishedAt') or x.get('published_date') or '') for x in rs if x.get('publishedAt') or x.get('published_date')] or ['']),'urls':links[:8],'reports':rs[:8]})
 events.sort(key=lambda e:(e['reportCount'],e['sourceCount'],e['lastSeen']),reverse=True)
 payload={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'window':'recent public reporting','method':'anchor-aware title clustering with category and publication-time agreement; candidate grouping only, not proof reports describe identical facts','events':events[:80]}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(f'LIVE EVENTS: {len(payload["events"])} clusters from {len(reports)} unique reports')
if __name__=='__main__': main()
