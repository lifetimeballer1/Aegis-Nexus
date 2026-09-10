#!/usr/bin/env python3
"""Detect possible contradictions inside clustered live events.
Heuristic only: flags opposing claim language for human review; it does not decide which report is true.
"""
from __future__ import annotations
import json,re,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'
IN=DATA/'live_events.json'; OUT=DATA/'event_consistency.json'
NEGATION={'denied','deny','denies','denial','false','untrue','no evidence','did not','didn’t','not occurred','not happen','refuted'}
POSITIVE={'confirmed','confirm','confirms','verified','occurred','happened','struck','killed','injured','launched','attacked','captured'}
NUMBER_RE=re.compile(r'\b(?:killed|dead|injured|wounded|casualties|arrested|detained)\D{0,18}(\d{1,5})\b',re.I)
LOCATION_RE=re.compile(r'\b(?:in|near|outside|around|at)\s+([A-Z][A-Za-z.-]{2,}(?:\s+[A-Z][A-Za-z.-]{2,}){0,3})')
def clean(v): return re.sub(r'\s+',' ',str(v or '')).strip()
def words(s): return set(re.findall(r'[a-z]{3,}',clean(s).lower()))
def domain(url):
 try:
  from urllib.parse import urlparse
  return urlparse(url).netloc.lower().removeprefix('www.')
 except Exception:return ''
def analyze_event(e):
 rs=e.get('reports') or []; texts=[]
 for r in rs:
  t=clean(r.get('title') or r.get('name'))
  if t:texts.append({'title':t,'url':clean(r.get('original_link') or r.get('url') or r.get('link')),'domain':domain(r.get('original_link') or r.get('url') or r.get('link'))})
 neg=[x for x in texts if any(p in x['title'].lower() for p in NEGATION)]
 pos=[x for x in texts if any(p in x['title'].lower() for p in POSITIVE)]
 nums=[]
 for x in texts:
  for m in NUMBER_RE.finditer(x['title']): nums.append((int(m.group(1)),x))
 locations=[]
 for x in texts:
  for m in LOCATION_RE.finditer(x['title']): locations.append((clean(m.group(1)),x))
 flags=[]
 if neg and pos: flags.append({'type':'claim-polarity','severity':'high','reason':'Reports use opposing confirmation/denial language.'})
 if len({n for n,_ in nums})>=2 and len(nums)>=2: flags.append({'type':'casualty-count','severity':'moderate','reason':'Reports cite different casualty counts.'})
 if len({loc.lower() for loc,_ in locations})>=2: flags.append({'type':'location','severity':'moderate','reason':'Reports name different locations.'})
 domains=sorted({x['domain'] for x in texts if x['domain']})
 level='high' if any(f['severity']=='high' for f in flags) else 'moderate' if flags else 'none'
 return {'eventId':e.get('id'),'title':e.get('title'),'consistency':level,'flagCount':len(flags),'flags':flags,'reviewRecommended':bool(flags),'sourceDomains':domains[:12],'reports':texts[:8]}
def main():
 if not IN.exists(): raise SystemExit('live_events.json missing')
 d=json.loads(IN.read_text(encoding='utf-8')); events=d.get('events') or []
 out=[analyze_event(e) for e in events]
 flagged=[x for x in out if x['flagCount']]
 payload={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'method':'heuristic contradiction signals from report titles; flags require human review and are not truth judgments','events':out[:80],'flaggedEvents':flagged[:40],'summary':{'eventsAnalyzed':len(out),'eventsFlagged':len(flagged),'highSeverity':sum(1 for x in flagged if x['consistency']=='high')}}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(f'EVENT CONSISTENCY: analyzed {len(out)}, flagged {len(flagged)}, high severity {payload["summary"]["highSeverity"]}')
if __name__=='__main__': main()
