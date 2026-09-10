#!/usr/bin/env python3
"""Build transparent, evidence-aware event intelligence.
No API key required. Scores are monitoring aids, not truth probabilities.
"""
# Quality model: corroboration must reflect independent reporting groups,
# source quality, concentration, and contradiction signals; raw article volume
# must never be allowed to masquerade as confirmation.
from __future__ import annotations
import json,re
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; EVENTS=DATA/'live_events.json'; OUT=DATA/'event_intelligence.json'
STOP=set('the a an and or of to in on for from with by as at is are was were has have had this that report reports reported says said after before over into near amid during its their his her'.split())
COUNTRIES={'afghanistan','algeria','angola','argentina','armenia','australia','azerbaijan','belarus','belgium','benin','bolivia','brazil','burkina faso','burundi','cameroon','canada','chad','chile','china','colombia','croatia','cuba','cyprus','denmark','egypt','eritrea','estonia','ethiopia','finland','france','georgia','germany','ghana','greece','guatemala','guinea','haiti','honduras','hungary','india','indonesia','iran','iraq','ireland','israel','italy','japan','jordan','kazakhstan','kenya','kosovo','lebanon','libya','lithuania','malaysia','mali','mexico','moldova','mongolia','morocco','mozambique','myanmar','nato','nepal','netherlands','niger','nigeria','north korea','norway','pakistan','peru','philippines','poland','portugal','qatar','romania','russia','rwanda','saudi arabia','senegal','serbia','somalia','south africa','south sudan','spain','sri lanka','sudan','sweden','switzerland','syria','taiwan','tajikistan','tanzania','thailand','tunisia','turkey','turkmenistan','uganda','ukraine','united arab emirates','united kingdom','united states','uzbekistan','venezuela','vietnam','yemen','zambia','zimbabwe'}
REGIONS={'sahel':{'mali','burkina faso','niger','chad'},'horn of africa':{'somalia','ethiopia','eritrea','djibouti','sudan','south sudan'},'great lakes':{'drc','rwanda','burundi','uganda'},'middle east':{'iran','iraq','israel','syria','lebanon','yemen','jordan','saudi arabia','qatar','united arab emirates'},'europe':{'ukraine','russia','belarus','poland','germany','france','united kingdom'},'east asia':{'china','taiwan','japan','south korea','north korea'},'latin america':{'mexico','brazil','colombia','venezuela','peru','argentina','chile'}}
AGGREGATORS={'news.google.com','news.yahoo.com','yahoo.com','msn.com','aol.com','apple.news','x.com','twitter.com','facebook.com','instagram.com','tiktok.com','youtube.com','reddit.com','t.me'}
PRIMARY={'un.org','nato.int','iaea.org','who.int','imf.org','worldbank.org','state.gov','defense.gov','whitehouse.gov','congress.gov','europa.eu','gov.uk','gov.ua','kremlin.ru','president.gov.ua'}
MAJOR={'reuters.com','apnews.com','bbc.com','bbc.co.uk','aljazeera.com','france24.com','dw.com','ft.com','bloomberg.com','wsj.com','nytimes.com','washingtonpost.com','theguardian.com','cnn.com','npr.org','pbs.org','cnbc.com','politico.com','economist.com','abcnews.go.com','cbsnews.com','nbcnews.com','skynews.com'}
SPECIALIST={'crisisgroup.org','acleddata.com','cfr.org','csis.org','iiss.org','sipri.org','reliefweb.int','unhcr.org','ohchr.org','ecfr.eu','rusi.org','bellingcat.com'}
def load(name,default):
 try:return json.loads((DATA/name).read_text(encoding='utf-8'))
 except Exception:return default
def clean(s):return re.sub(r'\s+',' ',str(s or '')).strip()
def tokens(s):return {x for x in re.findall(r'[a-z0-9]{4,}',clean(s).lower()) if x not in STOP}
def domain(url):
 try:return urlparse(str(url or '')).netloc.lower().removeprefix('www.')
 except:return ''
def report_url(r):
 credit=r.get('credit') or {}
 if isinstance(credit,str):
  try:credit=json.loads(credit)
  except Exception:credit={}
 return str(r.get('original_link') or r.get('url') or r.get('link') or credit.get('url') or credit.get('sourceUrl') or '')
def candidates(text):
 low=clean(text).lower();return [c for c in sorted(COUNTRIES,key=len,reverse=True) if re.search(r'(?<![a-z])'+re.escape(c)+r'(?![a-z])',low)][:8]
def region_hits(entities):return [{'region':rg,'entities':sorted(set(entities)&members)} for rg,members in REGIONS.items() if set(entities)&members]
def reporting_groups(reports):
 groups=[]
 for r in reports:
  ts=tokens(r.get('title') or r.get('name'))
  if not ts:continue
  for g in groups:
   if len(ts&g['tokens'])/max(1,len(ts|g['tokens']))>=.82:g['reports'].append(r);g['tokens']|=ts;break
  else:groups.append({'tokens':ts,'reports':[r]})
 return groups
def quality(d):
 if not d:return 25
 if d in PRIMARY or d.endswith('.gov') or d.endswith('.mil'):return 100
 if d in MAJOR:return 90
 if d in SPECIALIST:return 82
 if d in AGGREGATORS:return 25 if d not in {'news.google.com','news.yahoo.com','yahoo.com','msn.com','aol.com','apple.news'} else 35
 return 55
def grade(score,groups,domains,high_flags):
 if high_flags:return 'D'
 if score>=82 and groups>=4 and domains>=4:return 'A'
 if score>=68 and groups>=3 and domains>=3:return 'B'
 if score>=50 and groups>=2 and domains>=2:return 'C'
 return 'D'
def main():
 ev=load('live_events.json',{'events':[]}); se_all=load('source_evidence.json',{}); consistency=load('event_consistency.json',{})
 consistency_by={x.get('eventId'):x for x in consistency.get('events',[]) if isinstance(x,dict)}; output=[]
 for e in ev.get('events',[]):
  if not isinstance(e,dict):continue
  reports=[r for r in e.get('reports',[]) if isinstance(r,dict)]; text=' '.join([clean(e.get('title'))]+[clean(r.get('title') or r.get('name')) for r in reports]); entities=candidates(text)
  domains=[];times=[];urls=[]
  for r in reports:
   u=report_url(r);d=domain(u)
   if d:domains.append(d)
   if u:urls.append(u)
   t=clean(r.get('publishedAt') or r.get('published_date') or r.get('time'))
   if t:times.append(t)
  counts=Counter(domains); unique_domains=sorted(set(domains)); groups=reporting_groups(reports); group_count=len(groups); se=next((x for x in se_all.get('eventSourceEvidence',[]) if x.get('eventId')==e.get('id')),{}) or {}
  non_agg=[d for d in unique_domains if d not in AGGREGATORS]; concentration=max(counts.values(),default=0)/max(1,len(domains)); avg_quality=round(sum(quality(d) for d in domains)/len(domains)) if domains else 0
  primary=int(se.get('primarySourceDomains',0)); major=int(se.get('majorNewsDomains',0)); flags=consistency_by.get(e.get('id'),{}).get('flags',[]) or []; high_flags=sum(1 for f in flags if f.get('severity')=='high'); moderate_flags=sum(1 for f in flags if f.get('severity')=='moderate')
  score=20+min(32,group_count*10)+min(24,len(non_agg)*6)+min(14,avg_quality/7)+min(8,primary*4+major*2)-min(18,max(0,(concentration-.5)*36))-high_flags*18-moderate_flags*8
  if group_count<=1:score=min(score,44)
  elif group_count==2:score=min(score,62)
  elif group_count==3:score=min(score,78)
  score=max(0,min(95,round(score))); g=grade(score,group_count,len(non_agg),high_flags); status={'A':'well-corroborated','B':'moderately corroborated','C':'limited corroboration','D':'insufficient / conflicting evidence'}[g]; caveats=[]
  if len(non_agg)<3:caveats.append('Fewer than three non-aggregator domains observed')
  if group_count<2:caveats.append('Only one independent reporting group detected')
  if concentration>.5:caveats.append('Reporting is concentrated in one domain')
  if primary==0:caveats.append('No first-party institutional source identified in the observed reports')
  if high_flags:caveats.append('Conflicting confirmation/denial language requires human review')
  if moderate_flags:caveats.append('Reports contain materially different details that require review')
  caveats.append('Source class and domain diversity are proxies; they do not establish truth or source independence')
  timeline=sorted([{'time':t,'type':'report'} for t in times],key=lambda x:x['time'])[-8:]
  output.append({'eventId':e.get('id'),'title':e.get('title'),'category':e.get('category'),'reportedConfidence':e.get('confidence','unknown'),'evidenceGrade':g,'evidenceStatus':status,'corroborationScore':score,'reportCount':len(reports),'uniqueSourceDomains':len(unique_domains),'nonAggregatorDomains':len(non_agg),'independentReportingGroups':group_count,'sourceIndependence':se.get('independence','low'),'averageSourceQuality':avg_quality,'primarySourceDomains':primary,'majorNewsDomains':major,'domainConcentration':round(concentration,3),'consistency':consistency_by.get(e.get('id'),{}).get('consistency','unknown'),'consistencyFlags':flags,'sourceDomains':unique_domains[:10],'entityCandidates':entities,'regionalContext':region_hits(entities),'timeline':timeline,'sourceBreakdown':dict(counts.most_common(8)),'evidenceUrls':list(dict.fromkeys(urls))[:8],'caveats':caveats})
 rank={'A':4,'B':3,'C':2,'D':1}; output.sort(key=lambda x:(rank.get(x['evidenceGrade'],0),x['corroborationScore'],x['reportCount']),reverse=True)
 payload={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'version':2,'method':'Conservative evidence grading using independent headline groups, non-aggregator domains, source-class quality, concentration and contradiction signals. Scores are monitoring aids, not truth probabilities.','gradeScale':{'A':'Well-corroborated: multiple independent groups and diverse non-aggregator sources.','B':'Moderately corroborated: useful multi-source support, but important limitations remain.','C':'Limited corroboration: some support, insufficient independence for strong confidence.','D':'Insufficient or conflicting evidence: treat as a lead, not an established fact.'},'disclaimer':'Domain reputation is a heuristic. A reputable source can be wrong, and multiple outlets can repeat the same underlying report. Primary-source status does not make a claim true.','events':output[:80]}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print(f'EVENT INTELLIGENCE: {len(output)} events graded')
if __name__=='__main__':main()
