#!/usr/bin/env python3
"""Resolve target roles when the canonical extractor classified the target as an actor.

Only reclassifies an existing actor when that actor's canonical name/alias occurs in
an explicit action-object clause in the event's own source evidence. No article-wide
co-mention inference is allowed.
"""
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'
PATH=DATA/'canonical_intelligence.json'; LIVE=DATA/'live_articles.json'
PATTERNS={
 'sanction':(
  r'\bsanctions?\s+(?:on|against)\s+([^.;,:!?]+)',
  r'\b(?:impos(?:e|es|ed|ing)|expand(?:s|ed|ing)?|tighten(?:s|ed|ing)?)\b[^.;,:!?]{0,100}\bsanctions?\s+(?:on|against)\s+([^.;,:!?]+)',
 ),
 'military_action':(
  r'\b(?:strike|strikes|struck|attack|attacks|attacked|bombed|bombing|target|targets|targeted|targeting)\b(?:\s+(?:on|against))?\s+([^.;,:!?]+)',
  r'\b(?:military|armed)\s+(?:operation|action|campaign)\b[^.;,:!?]{0,100}\b(?:against|targeting|on)\s+([^.;,:!?]+)',
 ),
 'diplomatic_action':(
  r'\b(?:talks?|negotiat(?:e|es|ed|ing)|meet(?:s|ing)?|summit)\b\s+(?:with|between)\s+([^.;,:!?]+)',
  r'\b(?:support(?:s|ed|ing)?|back(?:s|ed|ing)?|oppose(?:s|d|ing)?|urge(?:s|d|ing)?|appeal(?:s|ed|ing)?)\b\s+(?:for|to|of|against|toward)\s+([^.;,:!?]+)',
  r'\b(?:agreement|accord|treaty)\b\s+(?:with|between)\s+([^.;,:!?]+)',
 ),
 'trade_action':(
  r'\b(?:trade|trades|trading|exports?|imports?)\b\s+(?:with|between)\s+([^.;,:!?]+)',
  r'\b(?:trade|trades|trading|exports?|imports?)\b\s+(?:to|from)\s+([^.;,:!?]+)',
  r'\b(?:tariffs?|trade restrictions?|anti-dumping measures?|anti-dumping duties?)\b\s+(?:on|against|toward|from)\s+([^.;,:!?]+)',
 ),
 'economic_action':(
  r'\b(?:tariffs?|taxes?|restrictions?|controls?)\b\s+(?:on|against|toward)\s+([^.;,:!?]+)',
  r'\b(?:measures?|policies|policy|rulings?|decisions?|findings?)\b\s+(?:against|toward|targeting|on|concerning)\s+([^.;,:!?]+)',
 ),
 'technology_action':(
  r'\b(?:export controls?|chip restrictions?|technology restrictions?)\b\s+(?:on|against|toward)\s+([^.;,:!?]+)',
  r'\b(?:restrict(?:s|ed|ing)?|ban(?:s|ned|ning)?|control(?:s|led|ling)?|limit(?:s|ed|ing)?)\b[^.;,:!?]{0,80}\b(?:to|for|against|on)\s+([^.;,:!?]+)',
 ),
 'energy_action':(
  r'\b(?:supply|supplies|supplied|supplying|export(?:s|ed|ing)?|import(?:s|ed|ing)?)\b\s+(?:oil|gas|lng|energy|electricity)\s+(?:to|from)\s+([^.;,:!?]+)',
  r'\b(?:oil|gas|lng|energy|electricity)\b[^.;,:!?]{0,80}\b(?:suppl(?:y|ies|ied|ying)|export(?:s|ed|ing)?|import(?:s|ed|ing)?)\b\s+(?:to|from)\s+([^.;,:!?]+)',
 ),
 'cyber_activity':(
  r'\b(?:cyberattack|cyberattacks|hack(?:s|ed|ing)?|hacking)\b\s+(?:against|on|targeting)\s+([^.;,:!?]+)',
  r'\b(?:cyber|hackers?|hacking|intrusion|intrusions|campaign|campaigns|operation|operations)\b[^.;,:!?]{0,120}\b(?:target(?:s|ed|ing)?|attack(?:s|ed|ing)?|hit|hits|struck|strikes)\s+(?:at\s+)?([^.;,:!?]+)',
  r'\b(?:cyber|hackers?|hacking)\b[^.;,:!?]{0,120}\b(?:against|on)\s+([^.;,:!?]+)',
 ),
 'political_action':(
  r'\b(?:support(?:s|ed|ing)?|back(?:s|ed|ing)?|oppos(?:e|es|ed|ing)|urge(?:s|d|ing)?|recogniz(?:e|es|ed|ing)?)\b\s+(?:for|of|on|against|toward)?\s*([^.;,:!?]+)',
  r'\b(?:pressure|pressures|pressured|threaten(?:s|ed|ing)?|demand(?:s|ed|ing)?|punish(?:es|ed|ing)?)\b\s+(?:on|against|over|for)?\s*([^.;,:!?]+)',
 ),
}
def text(a): return ' '.join(str(a.get(k) or '') for k in ('title','summary_snippet','summary','description','content')).strip()
def norm(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def names(e):
 out=[str(e.get('canonical_name') or '')]
 for a in e.get('aliases') or []:
  a=str(a or '').strip()
  if a and a not in out and a not in {'institution_context','context_resolved'}: out.append(a)
 return sorted(out,key=len,reverse=True)
def main():
 data=json.loads(PATH.read_text(encoding='utf-8')); live=json.loads(LIVE.read_text(encoding='utf-8'))
 articles={norm(a.get('url')):a for a in live.get('articles',[]) if isinstance(a,dict) and a.get('url')}
 evidence={str(e.get('id')):e for e in data.get('evidence',[]) if isinstance(e,dict)}
 entities={str(e.get('id')):e for e in data.get('entities',[]) if isinstance(e,dict)}
 repaired=0; events=0
 for ev in data.get('events',[]):
  if ev.get('target_ids'): continue
  pats=PATTERNS.get(str(ev.get('event_type') or ''),())
  if not pats: continue
  actors=[str(x) for x in ev.get('actor_ids',[]) if str(x) in entities]
  if not actors: continue
  source=[]
  for eid in ev.get('evidence_ids',[]):
   item=evidence.get(str(eid));
   if not item: continue
   a=articles.get(norm(item.get('url')))
   source.append(text(a) if a else ' '.join(str(item.get(k) or '') for k in ('title','excerpt')))
  for txt in source:
   for pat in pats:
    for m in re.finditer(pat,txt,re.I):
     clause=m.group(1)
     hits=[]
     for aid in actors:
      for n in names(entities[aid]):
       if n and re.search(r'(?<![A-Za-z])'+re.escape(n)+r'(?![A-Za-z])',clause,re.I): hits.append(aid);break
     if hits:
      ev['target_ids']=list(dict.fromkeys(hits)); ev['actor_ids']=[x for x in ev.get('actor_ids',[]) if str(x) not in hits]
      repaired+=len(hits);events+=1;break
    if ev.get('target_ids'): break
   if ev.get('target_ids'): break
 data.setdefault('metadata',{})['actor_target_role_repair']='explicit-clause-existing-actor-v2'
 data['metadata']['actor_target_role_repairs']=repaired
 PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'PASS: actor-target role repair repaired_targets={repaired} events={events}')
 return 0
if __name__=='__main__': raise SystemExit(main())