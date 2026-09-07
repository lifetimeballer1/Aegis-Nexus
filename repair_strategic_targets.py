#!/usr/bin/env python3
"""Repair missed U.S./China event targets from explicit source clauses only.

This stage never creates a target from article-wide co-mention. A candidate must
already be a canonical entity and its canonical name or known alias must occur in
the object clause of an action construction tied to the event's own evidence.
"""
from __future__ import annotations
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
CANONICAL=DATA/'canonical_intelligence.json'
LIVE=DATA/'live_articles.json'

PATTERNS={
 'sanction':(
  r'\b(?:impose|imposes|imposed|imposing|expand|expanded|expands|tighten|tightened|tightens)\b[^.;:!?]{0,100}\bsanctions?\b\s+(?:on|against)\s+([^.;:!?]+)',
  r'\bsanctions?\b\s+(?:on|against)\s+([^.;:!?]+)',
  r'\b(?:countermeasures?|retaliatory measures?)\b\s+(?:against|on)\s+([^.;:!?]+)',
 ),
 'military_action':(
  r'\b(?:strike|strikes|struck|attack|attacks|attacked|bombed|bombing|military operation)\b\s+(?:on|against|targeting)\s+([^.;:!?]+)',
  r'\b(?:target|targets|targeted|targeting)\b\s+([^.;:!?]+)',
  r'\b(?:deploy|deploys|deployed|deploying)\b\s+(?:troops|forces|ships|aircraft|missiles)?\s*(?:to|toward|into)\s+([^.;:!?]+)',
 ),
 'diplomatic_action':(
  r'\b(?:talks?|negotiat(?:e|es|ed|ing)|meet(?:s|ing)?|summit)\b\s+(?:with|between)\s+([^.;:!?]+)',
  r'\b(?:agreement|accord|treaty)\b\s+(?:with|between)\s+([^.;:!?]+)',
 ),
 'trade_action':(
  r'\b(?:trade|trades|trading|exports?|imports?)\b\s+(?:with|between)\s+([^.;:!?]+)',
  r'\b(?:export|import)\s+(?:controls?|restrictions?|bans?)\s+(?:on|against|toward|to)\s+([^.;:!?]+)',
  r'\b(?:tariffs?|trade restrictions?)\b\s+(?:on|against|toward)\s+([^.;:!?]+)',
 ),
 'economic_action':(
  r'\b(?:tariffs?|taxes?|restrictions?|controls?)\b\s+(?:on|against|toward)\s+([^.;:!?]+)',
  r'\b(?:investment|invests?|invested|investing)\b\s+(?:in|into)\s+([^.;:!?]+)',
 ),
 'technology_action':(
  r'\b(?:restrict(?:s|ed|ing)?|ban(?:s|ned|ning)?|control(?:s|led|ling)?|limit(?:s|ed|ing)?)\b\s+(?:exports?|chips?|technology|semiconductors?)\s+(?:to|for|against)\s+([^.;:!?]+)',
  r'\b(?:export controls?|chip restrictions?|technology restrictions?)\b\s+(?:on|against|toward)\s+([^.;:!?]+)',
 ),
 'energy_action':(
  r'\b(?:supply|supplies|supplied|supplying|export(?:s|ed|ing)?|import(?:s|ed|ing)?)\b\s+(?:oil|gas|lng|energy|electricity)\s+(?:to|from)\s+([^.;:!?]+)',
 ),
 'cyber_activity':(
  r'\b(?:cyberattack|cyberattacks|hack(?:s|ed|ing)?|hacking)\b\s+(?:against|on|targeting)\s+([^.;:!?]+)',
 ),
 'political_action':(
  r'\b(?:support(?:s|ed|ing)?|back(?:s|ed|ing)?|oppos(?:e|es|ed|ing))\b\s+([^.;:!?]+)',
 ),
}

def article_text(a):
 return ' '.join(str(a.get(k) or '') for k in ('title','summary_snippet','summary','description','content')).strip()

def norm(s):
 return re.sub(r'\s+',' ',str(s or '')).strip()

def boundary(pattern,text):
 return re.compile(r'(?<![A-Za-z])'+pattern+r'(?![A-Za-z])',re.I)

def evidence_articles(data):
 try: raw=json.loads(LIVE.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError): raw={}
 articles=raw.get('articles',[]) if isinstance(raw,dict) else []
 by_url={norm(a.get('url')):a for a in articles if isinstance(a,dict) and a.get('url')}
 by_title={norm(a.get('title')).casefold():a for a in articles if isinstance(a,dict) and a.get('title')}
 evidence={str(e.get('id')):e for e in data.get('evidence',[]) if isinstance(e,dict)}
 return by_url,by_title,evidence

def candidate_names(entity):
 names=[str(entity.get('canonical_name') or '')]
 aliases=entity.get('aliases') or []
 for alias in aliases:
  alias=str(alias or '').strip()
  if alias and alias not in names and alias not in {'institution_context','context_resolved'}: names.append(alias)
 return sorted(names,key=len,reverse=True)

def main():
 data=json.loads(CANONICAL.read_text(encoding='utf-8'))
 by_url,by_title,evidence=evidence_articles(data)
 entities={str(e.get('id')):e for e in data.get('entities',[]) if isinstance(e,dict)}
 repaired=0
 details=[]
 for event in data.get('events',[]):
  if event.get('target_ids'): continue
  event_type=str(event.get('event_type') or '')
  patterns=PATTERNS.get(event_type,())
  if not patterns: continue
  source_text=[]
  for eid in event.get('evidence_ids',[]):
   ev=evidence.get(str(eid))
   if not ev: continue
   article=by_url.get(norm(ev.get('url')))
   if article is None: article=by_title.get(norm(ev.get('title')).casefold())
   if article: source_text.append(article_text(article))
   else:
    fallback=' '.join(str(ev.get(k) or '') for k in ('title','excerpt')).strip()
    if fallback: source_text.append(fallback)
  if not source_text: continue
  actors={str(x) for x in event.get('actor_ids',[]) if x}
  candidates=[(eid,entity) for eid,entity in entities.items() if eid not in actors]
  for text in source_text:
   for pat in patterns:
    for match in re.finditer(pat,text,re.I):
     clause=match.group(1)
     found=[]
     for eid,entity in candidates:
      for name in candidate_names(entity):
       if boundary(re.escape(name),clause).search(clause):
        found.append(eid);break
     if found:
      event['target_ids']=list(dict.fromkeys(found))
      repaired+=len(event['target_ids'])
      details.append((event.get('id'),event_type,event['target_ids']))
      break
    if event.get('target_ids'): break
   if event.get('target_ids'): break
 data.setdefault('metadata',{})['explicit_target_repair_v2']='evidence-clause-alias-v2'
 data['metadata']['explicit_target_repairs_v2']=repaired
 CANONICAL.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'PASS: strategic target repair repaired_targets={repaired} events={len(details)}')
 for event_id,event_type,target_ids in details[:20]: print(f'  {event_type} {event_id}: targets={target_ids}')
 return 0

if __name__=='__main__': raise SystemExit(main())
