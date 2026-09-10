#!/usr/bin/env python3
"""Repair missed event targets from explicit source clauses only.

A candidate must already be a canonical entity and its canonical name or known
alias must occur in an explicit object/partner clause tied to the event's own
source evidence. Article-wide co-mention is never sufficient.
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
  r'\b(?:talks?|negotiat(?:e|es|ed|ing)|meet(?:s|ing)?|met|summit)\b\s+(?:with|between)\s+([^.;:!?]+)',
  r'\b(?:meet(?:s|ing)?|met)\b\s+(?:with\s+)?([^.;:!?]+)',
  r'\b(?:agreement|accord|treaty)\b\s+(?:with|between)\s+([^.;:!?]+)',
  r'\b(?:support(?:s|ed|ing)?|back(?:s|ed|ing)?|oppose(?:s|d|ing)?|urge(?:s|d|ing)?|recogniz(?:e|es|ed|ing)?)\b\s+(?:for|of|on|against|toward)\s+([^.;:!?]+)',
  r'\b(?:support|backing|opposition|appeal)\b\s+(?:for|to)\s+([^.;:!?]+)',
  r'\b[A-Za-z]+-([A-Za-z]+)\s+(?:delimitation\s+)?(?:talks|summit|meetings?|negotiations?)\b',
 ),
 'trade_action':(
  r'\b(?:trade|trades|trading|exports?|imports?)\b\s+(?:with|between|to|from)\s+([^.;:!?]+)',
  r'\b(?:export|exports|exported|exporting|import|imports|imported|importing)\b\s+(?:controls?|restrictions?|bans?)\s+(?:on|against|toward|to|from)\s+([^.;:!?]+)',
  r'\b(?:tariffs?|trade restrictions?|anti-dumping measures?|anti-dumping duties?)\b\s+(?:on|against|toward|from|on imports? from)\s+([^.;:!?]+)',
  r'\b(?:dumping|anti-dumping)\b[^.;:!?]{0,100}\b(?:from|by|against)\s+([^.;:!?]+)',
  r'\b(?:trade\s+)?(?:surplus|deficit)\b\s+(?:with|against|versus|vs\.?)\s+([^.;:!?]+)',
  r'\btrade\s+(?:barbs|spats?|rows?|disputes?|fight|war|tensions?|frictions?)\b\s+(?:over|about|on|between|with)\s+([^.;:!?]+)',
  r'\b([A-Z][A-Za-z.()\-]{1,30}?)\s+trade\s+(?:deficit|surplus|gap|imbalance)\b',
  r'\b([A-Z][A-Za-z .\'’&\-()]{1,50}?)\s+(?:to\s+)?(?:demand|demands|seek|seeks|seeking|urge|urges|press|push|ask)\b[^.;:!?]{0,80}?\bfrom\s+(?:China|Chinese)\b',
  r'\b([A-Z][A-Za-z .\'’&\-()]{1,50}?)\s+(?:seek|seeks|seeking|demand|demands|request|requests|urge|urges)\b[^.;:!?]{0,80}?\bChinese\b[^.;:!?]{0,40}?\baction\b',
  r'\bfor\s+([A-Z][A-Za-z .\'’&\-()]{1,50}?)\s+(?:playing|teaming|aligning|partnering|siding|dealing|trading)\b[^.;:!?]{0,60}?\bwith\b',
 ),
 'economic_action':(
  r'\b(?:tariffs?|taxes?|restrictions?|controls?)\b\s+(?:on|against|toward)\s+([^.;:!?]+)',
  r'\b(?:investment|invests?|invested|investing)\b\s+(?:in|into)\s+([^.;:!?]+)',
  r'\b(?:measures?|policies|policy)\b\s+(?:against|toward|targeting)\s+([^.;:!?]+)',
  r'\b(?:ruling|rulings|decision|decisions|finding|finds|found)\b\s+(?:on|against|concerning)\s+([^.;:!?]+)',
 ),
 'technology_action':(
  r'\b(?:restrict(?:s|ed|ing)?|ban(?:s|ned|ning)?|control(?:s|led|ling)?|limit(?:s|ed|ing)?)\b\s+(?:exports?|chips?|technology|semiconductors?)\s+(?:to|for|against)\s+([^.;:!?]+)',
  r'\b(?:export controls?|chip restrictions?|technology restrictions?)\b\s+(?:on|against|toward)\s+([^.;:!?]+)',
  r'\b(?:sell|sells|sold|selling|provide|provides|provided|providing|supply|supplies|supplied|supplying)\b\s+(?:chips?|technology|semiconductors?|equipment)\s+(?:to|for)\s+([^.;:!?]+)',
  r'\b([A-Z][A-Za-z .\'’&\-()]{1,50}?)\s+(?:outlines?|announces?|announced|unveils?|unveiled|details?|detailed|reveals?|revealed|issues?|issued|prepares?|prepared)\b[^.;:!?]{0,40}?\bresponses?\b[^.;:!?]{0,80}?\bto\b',
 ),
 'energy_action':(
  r'\b(?:supply|supplies|supplied|supplying|export(?:s|ed|ing)?|import(?:s|ed|ing)?)\b\s+(?:oil|gas|lng|energy|electricity)\s+(?:to|from)\s+([^.;:!?]+)',
  r'\bpolic(?:y|ies)\b[^.;:!?]{0,40}?\btoward\s+([^.;:!?]+)',
 ),
 'cyber_activity':(
  r'\b(?:cyberattack|cyberattacks|hack(?:s|ed|ing)?|hacking)\b\s+(?:against|on|targeting)\s+([^.;:!?]+)',
  r'\b(?:cyber|hackers?|hacking)\b[^.;:!?]{0,80}\b(?:target(?:s|ed|ing)?|attack(?:s|ed|ing)?)\b\s+([^.;:!?]+)',
  r'\bthreats?\b\s+(?:to|against)\s+([^.;:!?]+)',
 ),
 'political_action':(
  r'\b(?:support(?:s|ed|ing)?|back(?:s|ed|ing)?|oppos(?:e|es|ed|ing)|urge(?:s|d|ing)?|call(?:s|ed|ing)? for|recogniz(?:e|es|ed|ing)?)\b\s+(?:for|of|on|against|toward)?\s*([^.;:!?]+)',
  r'\b([A-Z][A-Za-z .\'’&\-()]{1,50}?)\s+(?:outlines?|announces?|announced|unveils?|unveiled|details?|detailed|reveals?|revealed|issues?|issued|prepares?|prepared)\b[^.;:!?]{0,40}?\bresponses?\b[^.;:!?]{0,80}?\bto\b',
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
 for alias in entity.get('aliases') or []:
  alias=str(alias or '').strip()
  if alias and alias not in names and alias not in {'institution_context','context_resolved'}: names.append(alias)
 return sorted(names,key=len,reverse=True)

def match_targets(clause,entities):
 """Resolve only canonical entities explicitly present in the extracted clause.

 Longest-name-wins span suppression: a shorter alias fully contained in a longer
 match of a different entity (e.g. 'China' inside 'South China Sea') is ignored."""
 spans=[]
 for eid,entity in entities.items():
  for name in candidate_names(entity):
   if not name: continue
   pattern=boundary(re.escape(name),clause)
   for match in pattern.finditer(clause):
    spans.append((match.start(),match.end(),len(name),eid))
    break
 spans.sort(key=lambda s:(-(s[1]-s[0]),-s[2]))
 claimed=[]; found=[]
 for start,end,_,eid in spans:
  if any(start < cend and end > cstart for cstart,cend in claimed): continue
  claimed.append((start,end))
  if eid not in found: found.append(eid)
 return found

def main():
 data=json.loads(CANONICAL.read_text(encoding='utf-8'))
 by_url,by_title,evidence=evidence_articles(data)
 entities={str(e.get('id')):e for e in data.get('entities',[]) if isinstance(e,dict)}
 repaired=0; details=[]
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
  for text in source_text:
   for pat in patterns:
    for match in re.finditer(pat,text,re.I):
     clause=match.group(1)
     found=match_targets(clause,entities)
     if event_type=='diplomatic_action':
      found=[eid for eid in found if any(re.match(r'(?:the\s+)?'+re.escape(name)+r'(?![A-Za-z])',clause,re.I) for name in candidate_names(entities[eid]))]
     actor_set={str(aid) for aid in event.get('actor_ids',[])}
     found=[eid for eid in found if eid not in actor_set]
     if found:
      event['target_ids']=found
      repaired+=len(found); details.append((event.get('id'),event_type,found))
      break
    if event.get('target_ids'): break
   if event.get('target_ids'): break
 data.setdefault('metadata',{})['explicit_target_repair_v5']='evidence-clause-alias-v6'
 data['metadata']['explicit_target_repairs_v5']=repaired
 data['metadata']['explicit_target_actor_reclassification_v2']=True
 CANONICAL.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(f'PASS: strategic target repair repaired_targets={repaired} events={len(details)}')
 for event_id,event_type,target_ids in details[:20]: print(f'  {event_type} {event_id}: targets={target_ids}')
 return 0

if __name__=='__main__': raise SystemExit(main())
