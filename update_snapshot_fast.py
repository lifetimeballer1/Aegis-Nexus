#!/usr/bin/env python3
"""Parallel snapshot builder using the existing Global Pulse source catalog."""
from __future__ import annotations
import hashlib, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
import update_snapshot as base
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; SNAP=DATA/'snapshot.json'; HIST=DATA/'history.json'; SOURCES=DATA/'sources.json'; MAX_WORKERS=10; SCORE_VERSION=5
CLIMATE_RE=re.compile(r"\b(drought|water shortage|water stress|water scarcity|reservoir|water supply|flood|flooding|cyclone|hurricane|typhoon|storm surge|landslide|heatwave|heat wave|extreme heat|wildfire|forest fire|bushfire|extreme cold|food insecurity|food crisis|famine|acute hunger|hunger|crop failure|harvest failure|epidemic|outbreak|cholera|malaria|avian flu|pandemic|disease outbreak)\b",re.I)
MARKET_RE=re.compile(r"\b(stock market|stocks|shares|bond yields?|treasury yields?|currency|forex|exchange rate|dollar|euro|yen|yuan|oil prices?|crude prices?|natural gas prices?|market volatility|market selloff|market rally|volatility index)\b",re.I)
DRIVER_DEFS={
 'Conflict activity':(re.compile(r"\b(war|armed conflict|fighting|battle|offensive|airstrike|shelling|invasion|insurgent|insurgency|militant attack|clash|bombing|hostage crisis)\b",re.I),{'live','international','regional','middle-east','africa','americas','analysis'}),
 'Diplomatic strain':(base.DIPLO_RE,{'us-politics','world-politics','analysis'}),
 'Economic pressure':(base.ECON_RE,{'economics','international','regional','live'}),
 'Market volatility':(MARKET_RE,{'economics','international','regional','live'}),
 'Military posture':(base.MIL_RE,{'live','international','regional','middle-east','africa','americas','analysis'}),
 'Climate & humanitarian pressure':(CLIMATE_RE,{'climate-hazard','food-security','humanitarian','international','regional','live'})}

def parse_feed(label,url,kind):
 rows=[]; error=None
 try:
  root=ET.fromstring(base.fetch(url)); items=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
  for item in items[:18]:
   title=base.clean(base.text(item,'title') or base.text(item,'{http://www.w3.org/2005/Atom}title')); link=base.text(item,'link')
   if not link:
    node=item.find('{http://www.w3.org/2005/Atom}link'); link=node.attrib.get('href','') if node is not None else ''
   summary=base.clean(base.text(item,'description') or base.text(item,'{http://www.w3.org/2005/Atom}summary')); pub=base.text(item,'pubDate') or base.text(item,'updated') or base.text(item,'{http://www.w3.org/2005/Atom}updated')
   if title and link:
    breaking=base.is_breaking(title,summary); rows.append({'id':hashlib.sha1(link.encode()).hexdigest()[:12],'sourceLabel':label,'sourceType':kind,'title':title[:240],'summary':summary[:420],'source':link,'url':link,'time':pub,'tag':'Breaking' if breaking else 'World','confidence':'DEVELOPING','breaking':breaking})
 except Exception as exc: error=f'{label}: {type(exc).__name__}'
 return rows,error

def recency(s): return max(.05,base.recency_weight(s.get('time')))
def normalized_score(stories,regex,base_score=40,eligible=None,boost_terms=()):
 pool=[s for s in stories if eligible is None or s.get('sourceType') in eligible]
 if not pool:return int(base_score)
 total=sum(recency(s) for s in pool); matched=0
 for s in pool:
  text=f"{s.get('title','')} {s.get('summary','')}"; w=recency(s)
  if regex.search(text):
   matched+=w
   if boost_terms and any(re.search(term,text,re.I) for term in boost_terms): matched+=w*.35
 share=min(1,matched/max(total,.01)); return int(round(max(0,min(100,base_score+65*share))) )

def driver_evidence(stories,regex,eligible):
 pool=[s for s in stories if s.get('sourceType') in eligible]; matches=[]; domains=set(); recent=0; weighted=0; total=sum(recency(s) for s in pool)
 for s in pool:
  text=f"{s.get('title','')} {s.get('summary','')}"; w=recency(s)
  if regex.search(text):
   weighted+=w; matches.append(s)
   host=urlparse(s.get('url') or s.get('source') or '').netloc.lower()
   if host: domains.add(host)
   t=base.parse_time(s.get('time')); recent += 1 if t and (datetime.now(timezone.utc)-t).total_seconds() <= 86400 else 0
 matches.sort(key=lambda x:recency(x),reverse=True)
 return {'poolSize':len(pool),'matches':len(matches),'sources':len(domains),'recentMatches':recent,'signalRatio':round(weighted/max(total,.01),3) if total else 0,'topSignals':[{'title':s.get('title','')[:180],'source':s.get('sourceLabel',''),'url':s.get('url') or s.get('source',''),'time':s.get('time','')} for s in matches[:5]]}

def climate_metrics(stories):
 groups={'Drought & water':re.compile(r"\b(drought|water shortage|water stress|water scarcity|reservoir|water supply)\b",re.I),'Floods & storms':re.compile(r"\b(flood|flooding|cyclone|hurricane|typhoon|storm surge|landslide|glacier)\b",re.I),'Heat & fire':re.compile(r"\b(heatwave|heat wave|extreme heat|wildfire|forest fire|bushfire|extreme cold)\b",re.I),'Food security':re.compile(r"\b(famine|food insecurity|food crisis|acute hunger|hunger|crop failure|harvest failure|food shortage)\b",re.I),'Health outbreaks':re.compile(r"\b(epidemic|outbreak|cholera|malaria|avian flu|pandemic|disease outbreak)\b",re.I)}
 pool={'climate-hazard','food-security','humanitarian','international','regional','live'}
 return {name:normalized_score(stories,rx,25,pool) for name,rx in groups.items()}

def build_early_warning(tension,breakdown,history):
 points=[p for p in history if isinstance(p,dict) and p.get('scoreVersion')==SCORE_VERSION and isinstance(p.get('tension'),(int,float))]; recent=[float(p['tension']) for p in points[-12:]]; prior=[float(p['tension']) for p in points[-36:-12]]; ra=sum(recent)/len(recent) if recent else tension; pa=sum(prior)/len(prior) if prior else ra; momentum=round(ra-pa,1); name,val=max(breakdown.items(),key=lambda x:x[1]) if breakdown else ('Overall tension',tension); level='HIGH' if tension>=75 or momentum>=10 else 'ELEVATED' if tension>=55 or momentum>=5 else 'WATCH'; return {'level':level,'score':int(tension),'momentum':momentum,'direction':'rising' if momentum>=2 else 'falling' if momentum<=-2 else 'stable','strongestDriver':name,'strongestDriverScore':int(val),'method':'Current score model v5; recent 12 snapshots versus preceding 24 matching snapshots.'}

def refine_conflict_evidence(conflicts):
    """Remove cross-theater false positives and count corroboration by source domain."""
    definitions={c[0]:set(c[5]) for c in base.CONFLICTS}
    alias_users={}
    for cid, aliases in definitions.items():
        for alias in aliases: alias_users.setdefault(alias, set()).add(cid)
    ambiguous={a for a, users in alias_users.items() if len(users)>1}
    for c in conflicts:
        cid=c.get('id'); aliases=definitions.get(cid,set()); unique_aliases=aliases-ambiguous
        kept=[]
        for sig in c.get('signals',[]):
            blob=f"{sig.get('title','')} {' '.join(sig.get('match',[]))}"
            matched=set(sig.get('match',[]))
            if unique_aliases and matched & unique_aliases:
                kept.append(sig); continue
            if unique_aliases:
                if any(base.alias_present(a, blob) for a in unique_aliases): kept.append(sig)
            else: kept.append(sig)
        c['signals']=kept; c['signalCount']=len(kept)
        domains={urlparse(str(s.get('url',''))).netloc.lower() for s in kept if urlparse(str(s.get('url',''))).netloc}
        c['sourceCount']=len(domains)
        if len(domains)>=3: c['confidence']='CORROBORATED'
        elif len(domains)==2: c['confidence']='MULTI-SOURCE'
        elif len(domains)==1: c['confidence']='SINGLE-SOURCE'
        else: c['confidence']='MONITORING'
        if kept: c['lastSignal']=kept[0].get('time'); c['recent']=kept[0].get('title','')[:180]
        else: c['lastSignal']=None; c['recent']='No specific current signal passed the theater-specific evidence filter.'; c['status']='Monitoring'
        c['facts']=f"{len(kept)} conflict-specific signal(s) from {len(domains)} independent source domain(s) after theater and corroboration filtering."
        c['analysis']='Score is a monitoring signal based on theater-specific identifiers, event severity, source-domain breadth, and recency. Shared militant/group names alone cannot corroborate a theater. It is not a battlefield truth, casualty count, or war probability.'
    return conflicts

def main():
 DATA.mkdir(exist_ok=True); old=base.load_json(SNAP,{}); history=base.load_json(HIST,[]); stories=[]; errors=[]; feeds=list(dict.fromkeys(base.FEEDS))
 with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
  futures=[pool.submit(parse_feed,*feed) for feed in feeds]
  for f in as_completed(futures):
   rows,error=f.result(); stories.extend(rows); errors.append(error) if error else None
 unique=[]; seen=set()
 for s in stories:
  if s['id'] not in seen: seen.add(s['id']); unique.append(s)
 unique.sort(key=lambda s:base.parse_time(s['time']) or datetime.min.replace(tzinfo=timezone.utc),reverse=True); stories=unique[:300]
 old_ids={s.get('id') for s in old.get('stories',[])}; new_items=[s for s in stories if s['id'] not in old_ids]
 boosts={'Conflict activity':(r'airstrike',r'missile',r'drone',r'troops',r'offensive',r'shelling',r'invasion'),'Diplomatic strain':(r'sanction',r'expulsion',r'ultimatum',r'diplomatic crisis'),'Economic pressure':(r'tariff',r'sanction',r'supply disruption',r'recession'),'Market volatility':(r'selloff',r'plunge',r'surge',r'volatility'),'Military posture':(r'airstrike',r'missile',r'drone',r'troops',r'offensive',r'shelling',r'invasion'),'Climate & humanitarian pressure':()}
 breakdown={name:normalized_score(stories,rx,35 if name in ('Conflict activity','Military posture') else 32 if name not in ('Climate & humanitarian pressure',) else 25,pool,boosts[name]) for name,(rx,pool) in DRIVER_DEFS.items()}
 evidence={name:driver_evidence(stories,rx,pool) for name,(rx,pool) in DRIVER_DEFS.items()}; climate=climate_metrics(stories)
 weights={'Conflict activity':.22,'Diplomatic strain':.15,'Economic pressure':.16,'Market volatility':.10,'Military posture':.25,'Climate & humanitarian pressure':.12}; tension=round(sum(breakdown[k]*weights[k] for k in weights)); old_tension=old.get('tension'); delta=tension-old_tension if isinstance(old_tension,(int,float)) and old.get('scoreVersion')==SCORE_VERSION else 0
 changes=[{'kind':'breaking' if s['breaking'] else 'new reporting','title':s['title'][:150],'detail':f"{s['sourceLabel']} · {s['sourceType']} · {s['confidence']}"} for s in new_items[:10]] or [{'kind':'refresh','title':'Public sources checked — no new unique headlines','detail':f'{len(feeds)} feeds checked; {len(stories)} current stories retained.'}]
 conflicts=refine_conflict_evidence(base.make_conflicts(stories,old)); now=datetime.now(timezone.utc).isoformat(); hp=[p for p in history if isinstance(p,dict) and p.get('scoreVersion')==SCORE_VERSION]; hw=hp+[{'updatedAt':now,'tension':tension,'delta':delta,'scoreVersion':SCORE_VERSION}]; early=build_early_warning(tension,breakdown,hw)
 # CRITICAL: the 5-minute refresh owns news/scoring, but must never erase OSINT
 # map state produced by the regional, conflict-coverage, or other map workflows.
 # Preserve the whole osintMaps object so regionalPoints/counts/diagnostics survive
 # every refresh and remain available to Pages and the frontend.
 preserved_osint=old.get('osintMaps') if isinstance(old.get('osintMaps'),dict) else None
 snapshot={'updatedAt':now,'scoreVersion':SCORE_VERSION,'sourceStatus':f'{len(stories)} stories · {len(new_items)} new · {len(feeds)-len(errors)}/{len(feeds)} feeds healthy','dataNote':'Global Tension is a weighted monitoring index built from six distinct current signal pools. Driver evidence exposes matching stories and independent source domains; headline volume alone does not determine the score.','tension':tension,'tensionDelta':delta,'breakdownScores':breakdown,'driverSignals':evidence,'climatePressure':climate,'earlyWarning':early,'changes':changes,'conflicts':conflicts,'markers':old.get('markers',[]),'social':old.get('social',[]),'stories':stories,'sourceHealth':[{'name':label,'type':kind,'status':'failed' if any(e.startswith(label+':') for e in errors) else 'online'} for label,_,kind in feeds]}
 if preserved_osint is not None: snapshot['osintMaps']=preserved_osint
 SNAP.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n'); HIST.write_text(json.dumps(hw[-288:],ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n'); SOURCES.write_text(json.dumps({'updatedAt':now,'feeds':[{'name':a,'url':b,'type':c,'domain':urlparse(b).netloc} for a,b,c in feeds],'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n'); print(snapshot['sourceStatus'],'tension',tension,'early warning',early['level'],'conflicts',len(conflicts),'preserved_osint',bool(preserved_osint))
 if errors: print('errors:','; '.join(errors))
if __name__=='__main__': main()
