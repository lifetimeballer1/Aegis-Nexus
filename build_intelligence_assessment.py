#!/usr/bin/env python3
"""Build explainable, evidence-aware risk assessments from public data.
Scores are indicators, not forecasts or claims of causation.
"""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'
def load(name, default):
 try:return json.loads((DATA/name).read_text(encoding='utf-8'))
 except Exception:return default
def tokens(s):return set(re.findall(r'[a-z0-9]{4,}',str(s or '').lower()))
def clamp(x):return max(0,min(100,int(round(x))))
def main():
 snap=load('snapshot.json',{}); graph=load('intelligence_graph.json',{}); events=load('live_events.json',{}); breaking=load('breaking_news.json',{}); source_ev=load('source_evidence.json',{}); event_intel=load('event_intelligence.json',{}); consistency=load('event_consistency.json',{}); previous=load('intelligence_assessment.json',{})
 stories=snap.get('stories') or snap.get('articles') or []; articles=breaking.get('articles') or []; edges=graph.get('edges') or []
 names={}
 for n in graph.get('nodes') or []:
  label=str(n.get('label') or n.get('name') or n.get('id') or '').strip()
  if label:names[label]=n
 ei_by={x.get('eventId'):x for x in event_intel.get('events',[]) if isinstance(x,dict)}; con_by={x.get('eventId'):x for x in consistency.get('events',[]) if isinstance(x,dict)}
 grade_weight={'A':1.0,'B':0.88,'C':0.68,'D':0.45}
 def score_for(label):
  tl=tokens(label); evidence=military=diplomacy=economic=0
  for r in list(stories)+list(articles):
   text=str(r.get('title') or r.get('name') or '')+' '+str(r.get('summary') or r.get('description') or ''); low=text.lower()
   if not (tl & tokens(text)):continue
   evidence+=1
   military+=sum(1 for k in ('attack','missile','airstrike','bombing','troops','military','war','conflict') if k in low)
   diplomacy+=sum(1 for k in ('talks','ceasefire','negotiation','agreement','diplomatic') if k in low)
   economic+=sum(1 for k in ('oil','shipping','tariff','sanction','trade','inflation','market') if k in low)
  edge_count=sum(1 for e in edges if label.lower() in (str(e.get('source_label') or '')+' '+str(e.get('target_label') or '')).lower())
  live=[e for e in events.get('events') or [] if tl & tokens(e.get('title'))]
  live_hits=len(live); quality_values=[]
  for e in live:
   q=ei_by.get(e.get('id'),{}); quality_values.append(grade_weight.get(q.get('evidenceGrade','D'),.45))
  evidence_factor=(sum(quality_values)/len(quality_values)) if quality_values else (1.0 if evidence>=5 else .7 if evidence>=2 else .45)
  raw=min(28,evidence*1.4)+min(24,military*2.2)+min(14,economic*1.1)+min(10,edge_count*1.5)+min(12,live_hits*4)-min(10,diplomacy*1.2)
  score=clamp(raw*evidence_factor)
  factors=[]
  if military:factors.append({'label':'Conflict / military activity','delta':clamp(military*2.2*evidence_factor)})
  if live_hits:factors.append({'label':'Live event activity','delta':clamp(live_hits*4*evidence_factor)})
  if economic:factors.append({'label':'Economic / energy signals','delta':clamp(economic*1.1*evidence_factor)})
  if edge_count:factors.append({'label':'Evidence-backed network exposure','delta':clamp(edge_count*1.5*evidence_factor)})
  if diplomacy:factors.append({'label':'Diplomatic / de-escalation signals','delta':-clamp(diplomacy*1.2*evidence_factor)})
  return score,sorted(factors,key=lambda x:abs(x['delta']),reverse=True)[:6],evidence
 old={str(x.get('entity')):x for x in previous.get('assessments') or []}; assessments=[]
 for label in names:
  score,factors,evidence=score_for(label)
  if evidence<2 and score<15:continue
  level='CRITICAL' if score>=85 else 'HIGH' if score>=70 else 'ELEVATED' if score>=45 else 'WATCH'; prior=old.get(label); delta=score-int(prior.get('score',score)) if prior else 0
  assessments.append({'entity':label,'score':score,'level':level,'delta':delta,'trend':'UP' if delta>2 else 'DOWN' if delta<-2 else 'STABLE','factors':factors,'evidenceCount':evidence,'method':'Explainable indicator using reporting volume, live-event activity, network exposure, economic signals, de-escalation signals and event evidence quality. Not a forecast or causal probability.'})
 assessments.sort(key=lambda x:x['score'],reverse=True)
 impact=[]
 for e in (events.get('events') or [])[:30]:
  cat=e.get('category','general'); title=e.get('title','Live event'); intel=ei_by.get(e.get('id'),{}); cons=con_by.get(e.get('id'),{})
  implications={'conflict':['regional military escalation risk','energy and shipping exposure','NATO / alliance-response monitoring'],'economic':['market and supply-chain sensitivity','energy / trade exposure','inflation and logistics monitoring'],'diplomatic':['negotiation / escalation monitoring','sanctions and policy exposure','alliance-response monitoring'],'political':['political stability monitoring','policy and alliance exposure','protest / governance risk monitoring'],'disaster':['humanitarian and infrastructure pressure','transport / supply-chain disruption','emergency response monitoring']}.get(cat,['regional spillover monitoring','market and policy sensitivity','humanitarian / infrastructure exposure'])
  impact.append({'eventId':e.get('id'),'title':title,'category':cat,'evidenceGrade':intel.get('evidenceGrade','D'),'evidenceStatus':intel.get('evidenceStatus','unknown'),'corroborationScore':intel.get('corroborationScore',0),'reportedConfidence':intel.get('reportedConfidence',e.get('confidence','unknown')),'reportCount':intel.get('reportCount',e.get('reportCount',0)),'sourceCount':intel.get('uniqueSourceDomains',e.get('sourceCount',0)),'sourceIndependence':intel.get('sourceIndependence','unknown'),'consistency':cons.get('consistency',intel.get('consistency','unknown')),'consistencyFlags':cons.get('flags',intel.get('consistencyFlags',[])),'whyThisMatters':{'immediate':implications[0],'shortTerm':implications[1],'mediumTerm':implications[2]},'urls':intel.get('evidenceUrls',e.get('urls',[]))[:5]})
 changed=sorted([x for x in assessments if abs(x['delta'])>=3],key=lambda x:abs(x['delta']),reverse=True)[:12]
 out={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'version':2,'method':'Explainable indicator layer with evidence-quality gating. Scores are not forecasts; market relationships are not treated as causal.','assessments':assessments[:60],'eventImpacts':impact[:20],'whatChanged':changed,'sourceSummary':{'uniqueReportCount':source_ev.get('uniqueReportCount',0),'uniqueSourceDomains':source_ev.get('uniqueSourceDomains',0),'evidenceGrades':{g:sum(1 for e in event_intel.get('events',[]) if e.get('evidenceGrade')==g) for g in ('A','B','C','D')}}}
 (DATA/'intelligence_assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print(f'ASSESSMENT: {len(out["assessments"])} entity indicators / {len(out["eventImpacts"])} event impacts / {len(changed)} material changes')
if __name__=='__main__':main()
