#!/usr/bin/env python3
"""Build canonical intelligence using shared entity extraction and scoring."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from typing import Any
from intelligence_entity_extractor import extract_entities
from intelligence_scoring import entity_importance,event_confidence,event_score,evidence_score,event_severity,strategic_relevance,relationship_strength,recency_score,source_reliability,parse_timestamp
from intelligence_schema import empty_document,validate_document
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';INPUT=DATA/'live_articles.json';OUTPUT=DATA/'canonical_intelligence.json'
EVENT_PATTERNS=(("sanction",r"\b(sanction|sanctions|sanctioned|sanctioning)\b"),("military_action",r"\b(strike|strikes|airstrike|airstrikes|missile|bombing|deployment|deploys|military operation|troops|forces)\b"),("diplomatic_action",r"\b(meet|meets|meeting|talks|negotiat|diplomatic|envoy|summit|ceasefire)\b"),("economic_action",r"\b(stimulus|interest rate|rate cut|tariff|tariffs|tax|capital|investment|economic policy)\b"),("trade_action",r"\b(trade|exports?|imports?|supply chain|customs)\b"),("technology_action",r"\b(chip|chips|semiconductor|semiconductors|artificial intelligence|technology|tech)\b"),("energy_action",r"\b(oil|gas|lng|energy|electricity|power grid|nuclear|uranium)\b"),("cyber_activity",r"\b(cyber|cyberattack|cyberattacks|hacking|malware|ransomware)\b"),("political_action",r"\b(election|elections|vote|voting|parliament|congress|president|government)\b"))
RELATIONSHIP_PATTERNS=(("sanctions",r"(?:imposed|announced|issued|expanded|tightened)\s+(?:new\s+)?sanctions?\s+(?:on|against)"),("trades_with",r"(?:trade|trades|trading|exports?|imports?)\s+(?:with|between)"),("negotiates_with",r"(?:negotiat(?:e|es|ed|ing)|talks?|meet(?:s|ing)?|summit)\s+(?:with|between)"),("cooperates_with",r"(?:cooperat(?:e|es|ed|ing)|cooperation|joint|agreement)\s+(?:with|between)"),("military_action_against",r"(?:strike|strikes|airstrike|airstrikes|bomb(?:ed|ing)?|attack(?:ed|s|ing)?|military operation)\s+(?:on|against|targeting)"),("deploys_to",r"(?:deploy(?:ed|s|ing)?|troops|forces)\s+(?:to|into)"),("supplies",r"(?:suppl(?:y|ies|ied|ying)|provide(?:s|d)?|arms?)\s+(?:to|for)"),("invests_in",r"(?:invest(?:s|ed|ing)?|investment)\s+(?:in|into)"))
RELEVANCE_PATTERNS=(("military",r"\b(military|armed forces|troops|deployment|missile|airstrike|aircraft carrier|navy|army|air force|marines|defense|defence)\b",.95),("conflict",r"\b(war|conflict|invasion|attack|strike|ceasefire|battle|hostilities)\b",.95),("diplomacy",r"\b(diplomatic|diplomacy|summit|envoy|negotiat|talks|treaty|alliance|NATO|UN)\b",.85),("sanctions",r"\b(sanction|sanctions|export controls|asset freeze|embargo)\b",.90),("trade",r"\b(trade|tariff|tariffs|export|exports|import|imports|supply chain)\b",.75),("economy",r"\b(interest rate|central bank|stimulus|inflation|economic policy|investment|finance|financial)\b",.70),("technology",r"\b(chip|chips|semiconductor|semiconductors|artificial intelligence|cyber|technology)\b",.70),("energy",r"\b(oil|gas|LNG|energy|electricity|nuclear|uranium|pipeline)\b",.75),("political",r"\b(president|government|parliament|congress|election|elections|prime minister)\b",.65))
ACTION_CONTEXT={"sanction":r"sanction(?:s|ed|ing)?","military_action":r"strike|strikes|airstrike|airstrikes|missile|bombing|deployment|deploys|military operation|troops|forces","diplomatic_action":r"meet|meets|meeting|talks|negotiat|diplomatic|envoy|summit|ceasefire","economic_action":r"stimulus|interest rate|rate cut|tariff|tariffs|tax|capital|investment|economic policy","trade_action":r"trade|exports?|imports?|supply chain|customs","technology_action":r"chip|chips|semiconductor|artificial intelligence|technology|tech","energy_action":r"oil|gas|lng|energy|electricity|power grid|nuclear|uranium","cyber_activity":r"cyber|cyberattack|cyberattacks|hacking|malware|ransomware","political_action":r"election|elections|vote|voting|parliament|congress|president|government"}
STRATEGIC_COUNTRIES={"United States","China"}
STRATEGIC_INSTITUTIONS={"U.S. Department of Defense","U.S. Department of State","U.S. Treasury","U.S. Department of Commerce","U.S. Department of Justice","U.S. Congress","White House","People's Liberation Army","Communist Party of China","Chinese State Council","Chinese Central Military Commission","Chinese Ministry of Foreign Affairs","Chinese Ministry of Commerce"}
def stable_id(prefix,*parts):return f"{prefix}-{hashlib.sha256('|'.join(parts).encode('utf-8','ignore')).hexdigest()[:16]}"
def normalize_url(url):
 """Fold feed-mirror URL variants (scheme case, query/fragment, trailing slash) of the same link."""
 u=str(url or '').strip()
 if not u:return ''
 if '://' not in u:u='https://'+u
 try:
  from urllib.parse import urlsplit,urlunsplit
  p=urlsplit(u);path=p.path or ''
  if path!='/':path=path.rstrip('/')
  return urlunsplit(((p.scheme or 'https').lower(),(p.hostname or '').lower(),path,'',''))
 except Exception:return u.lower()
def url_host(url):
 try:
  from urllib.parse import urlsplit
  return (urlsplit(str(url or '')).hostname or '').lower()
 except Exception:return ''
def normalize_title(title):
 t=re.sub(r'\s+',' ',str(title or '').lower()).strip()
 return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]','',t)).strip()
def score_breakdown(ev,score):
 """Human-readable confidence reasoning for one evidence record."""
 try:quality=float(ev.get('quality',ev.get('evidence_quality',0.75)))
 except (TypeError,ValueError):quality=0.75
 rel=source_reliability(ev);rec=recency_score(ev.get('published_at'));relevance=float(ev.get('geopolitical_relevance') or 0.0)
 return f"reliability {rel:.2f} | recency {rec:.2f} | quality {max(0.0,min(1.0,quality)):.2f} | relevance {relevance:.2f} => score {score:.3f}"
def earlier_stamp(a,b):
 """Return the earlier of two timestamp strings; empty means unknown."""
 da,db=parse_timestamp(a),parse_timestamp(b)
 if da and db:return a if da<=db else b
 return a or b or ''
def article_text(a):return " ".join(str(a.get(k) or "") for k in ("title","summary_snippet","summary","description","content")).strip()
def classify_geopolitical_relevance(text,event_type=None):
 text=str(text or "");scores=[score for _,pattern,score in RELEVANCE_PATTERNS if re.search(pattern,text,re.I)];event_bonus={'sanction':.15,'military_action':.15,'diplomatic_action':.10,'trade_action':.08,'economic_action':.07,'technology_action':.07,'energy_action':.08,'cyber_activity':.12,'political_action':.05}.get(event_type,0.0) if event_type else 0.0
 if not scores and not event_bonus:return 0.0
 return max(0.0,min(1.0,max(scores,default=0.0)+event_bonus))
def relation_type(text):
 for kind,pattern in RELATIONSHIP_PATTERNS:
  if re.search(pattern,text,re.I):return kind
 return "mentioned_with"
def action_for(event_type):return {"sanction":"imposed or expanded sanctions","military_action":"conducted or reported military activity","diplomatic_action":"conducted diplomatic engagement","economic_action":"took economic policy action","trade_action":"conducted trade activity","technology_action":"took technology-related action","energy_action":"took energy-related action","cyber_activity":"conducted or reported cyber activity","political_action":"took political action"}.get(event_type,"took an action")
def _near_action(text,event_type,start,end,window=140):
 pattern=ACTION_CONTEXT.get(event_type)
 if not pattern:return False
 left=text[max(0,start-window):start];right=text[end:min(len(text),end+window)]
 return bool(re.search(r"(?:^|\b)(?:"+pattern+r")(?:$|\b)",left,re.I) or re.search(r"(?:^|\b)(?:"+pattern+r")(?:$|\b)",right,re.I))
def _strategic_actor_signal(name,text,event_type):
 """Return confidence-like evidence that a U.S./China actor is tied to this action.

    A mere article co-mention is deliberately insufficient. The signal requires
    the canonical actor name/alias to occur in the same sentence or nearby action
    context, or a source-backed institution that is itself country-specific.
    """
 if name not in STRATEGIC_COUNTRIES and name not in STRATEGIC_INSTITUTIONS:return 0.0
 lowered=text.lower();aliases={name.lower()}
 if name=="United States":aliases.update({"united states","u.s.","u.s","usa","american"})
 elif name=="China":aliases.update({"china","chinese"})
 else:aliases.update({a.lower() for a in ("pentagon","dod","doj","white house","pla","ccp") if a in lowered})
 best=0.0
 for alias in aliases:
  for m in re.finditer(r"(?<![a-z])"+re.escape(alias)+r"(?![a-z])",lowered):
   sentence_start=max(lowered.rfind('.',0,m.start()),lowered.rfind('!',0,m.start()),lowered.rfind('?',0,m.start()))+1
   sentence_end=min([x for x in (lowered.find('.',m.end()),lowered.find('!',m.end()),lowered.find('?',m.end())) if x>=0] or [len(lowered)])
   sentence=lowered[sentence_start:sentence_end]
   action_match=re.search(ACTION_CONTEXT.get(event_type,r"\b(?:action|acted)\b"),sentence,re.I)
   if action_match:
    distance=abs((sentence_start+action_match.start())-m.start());score=.95 if distance<=80 else .80;best=max(best,score)
   elif _near_action(lowered,event_type,m.start(),m.end(),140):best=max(best,.70)
 return best
def participant_roles(found,matched,names,event_type,text):
    """Infer actors/targets from explicit action-object clauses, never article-wide co-mentions."""
    actors=[];targets=[];locations=[]
    actor_types={"person","government","government_agency","military","military_command","intelligence","political_party","company","financial_institution","international_organization","armed_group","country"}
    location_types={"region","location","conflict"}
    for eid in matched:
        etype=str(found.get(eid,{}).get("entity_type",""));name=names[eid]
        if etype in location_types:locations.append(eid)
        if etype in actor_types:
            if name in STRATEGIC_COUNTRIES or name in STRATEGIC_INSTITUTIONS:
                if _strategic_actor_signal(name,text,event_type)>=.70:actors.append(eid)
            else:actors.append(eid)
    target_patterns={
      "sanction":r"(?:impos(?:e|es|ed|ing)|expand(?:s|ed|ing)?|tighten(?:s|ed|ing)?)?\s*sanctions?\s+(?:on|against)\s+([^.;:!?]+)",
      "military_action":r"(?:strike|strikes|struck|attack|attacks|attacked|airstrike|bomb(?:ed|ing)?|operation|target(?:s|ed|ing)?)\s+(?:on|against|targeting)?\s*([^.;:!?]+)",
      "diplomatic_action":r"(?:talks?|negotiat(?:e|es|ed|ing)|meet(?:s|ing)?|met|summit)\s+(?:with|between)?\s*([^.;:!?]+)",
      "trade_action":r"(?:trade|trades|trading|export(?:s|ed|ing)?|import(?:s|ed|ing)?)\s+(?:with|between|to|from)\s+([^.;:!?]+)",
      "economic_action":r"(?:tariffs?|taxes?|restrictions?|controls?|measures?|policies|policy)\s+(?:on|against|toward|targeting)\s+([^.;:!?]+)",
      "technology_action":r"(?:restrict(?:s|ed|ing)?|ban(?:s|ned|ning)?|control(?:s|led|ling)?|limit(?:s|ed|ing)?|export controls?|chip restrictions?|technology restrictions?)\s+(?:on|against|toward|to|for)?\s*([^.;:!?]+)",
      "energy_action":r"(?:supply|supplies|supplied|supplying|export(?:s|ed|ing)?|import(?:s|ed|ing)?)\s+(?:oil|gas|lng|energy|electricity)\s+(?:to|from)\s+([^.;:!?]+)",
      "cyber_activity":r"(?:cyberattack|cyberattacks|hack(?:s|ed|ing)?|hacking)\s+(?:against|on|targeting)\s+([^.;:!?]+)",
      "political_action":r"(?:support(?:s|ed|ing)?|back(?:s|ed|ing)?|oppos(?:e|es|ed|ing)|urge(?:s|d|ing)?|call(?:s|ed|ing)?\s+for|recogniz(?:e|es|ed|ing)?)\s+([^.;:!?]+)",
    }
    target_pattern=target_patterns.get(event_type)
    if target_pattern:
        for m in re.finditer(target_pattern,text,re.I):
            clause=m.group(1).lower()
            # Diplomatic counterparts must lead the object phrase. A country
            # mentioned later in a news summary is not a participant in talks.
            for eid in matched:
                name=names[eid]
                aliases=[name]
                aliases.extend(str(a) for a in found.get(eid,{}).get("aliases",[]) if a)
                if any((re.match(r"(?:the\s+)?"+re.escape(alias)+r"(?![A-Za-z])",clause,re.I) if event_type=='diplomatic_action' else re.search(r"(?<![A-Za-z])"+re.escape(alias)+r"(?![A-Za-z])",clause,re.I)) for alias in aliases):
                    if eid not in targets:targets.append(eid)
            if targets:break
    if targets:actors=[x for x in actors if x not in targets]
    if not actors and targets:
        first_target=targets[0];target_name=names[first_target];target_pos=text.lower().find(target_name.lower());before=text[:target_pos] if target_pos>=0 else ''
        for eid in matched:
            if eid==first_target:continue
            name=names[eid]
            if name in STRATEGIC_COUNTRIES or name in STRATEGIC_INSTITUTIONS:
                if _strategic_actor_signal(name,text,event_type)>=.70:actors.append(eid)
            elif re.search(r"\b"+re.escape(name.lower())+r"\b",before.lower()):actors.append(eid)
    return actors,targets,locations
def main():
 if not INPUT.exists():print(f"ERROR: missing input {INPUT}");return 2
 try:raw=json.loads(INPUT.read_text(encoding='utf-8'))
 except json.JSONDecodeError as exc:print(f"ERROR: invalid input JSON: {exc}");return 2
 document=empty_document();document['metadata'].update({'input':str(INPUT.relative_to(ROOT)),'method':'shared-entity-extractor-v7','scoring':'shared-intelligence-scoring-v1','source_backed_only':True,'geopolitical_relevance':'canonical-context-v1','participant_model':'actor-target-location-v4','strategic_attribution':'action-local-v1'});entities={};evidence={};events={};relationships={};articles=raw.get('articles',[]) if isinstance(raw,dict) else [];discovered_ids=set();entity_event_scores={};entity_evidence_scores={};by_url={};by_host_title={};folded=0
 for article in articles:
  if not isinstance(article,dict):continue
  title,url=str(article.get('title') or '').strip(),str(article.get('url') or '').strip()
  if not title or not url:continue
  published=str(article.get('published_date') or '');text=article_text(article);event_types=[k for k,p in EVENT_PATTERNS if re.search(p,text,re.I)];article_relevance=classify_geopolitical_relevance(text,event_types[0] if event_types else None)
  nurl=normalize_url(url);host=url_host(nurl);ntitle=normalize_title(title)
  ev_id=by_url.get(nurl) or (by_host_title.get((host,ntitle)) if host and len(ntitle)>25 else None)
  if ev_id and ev_id in evidence:
   # Same-link variant or same-outlet re-issue: fold into the existing
   # evidence record instead of minting a duplicate that would inflate
   # mention counts, relationship weights, and tension tallies.
   ev=evidence[ev_id];folded+=1;ev['duplicate_count']=int(ev.get('duplicate_count') or 0)+1
   dup_urls=ev.setdefault('duplicate_urls',[])
   if url not in dup_urls and ev.get('url')!=url and len(dup_urls)<10:dup_urls.append(url)
   if published and (not ev.get('published_at') or earlier_stamp(published,ev.get('published_at'))==published):ev['published_at']=published
   ev_score=evidence_score(ev);ev['score_breakdown']=score_breakdown(ev,ev_score)
  else:
   ev_id=stable_id('evd',nurl or url,title);ev={'id':ev_id,'title':title,'source':str(article.get('source') or 'Unknown public source'),'url':url,'published_at':published,'reliability':article.get('reliability',.5),'quality':article.get('evidence_quality',.75),'geopolitical_relevance':article_relevance,'excerpt':str(article.get('summary_snippet') or '')[:500],'duplicate_count':0,'duplicate_urls':[]};evidence[ev_id]=ev;ev_score=evidence_score(ev);ev['score_breakdown']=score_breakdown(ev,ev_score);by_url.setdefault(nurl,ev_id)
   if host and len(ntitle)>25:by_host_title.setdefault((host,ntitle),ev_id)
  found_list=extract_entities(text);found={str(x['id']):x for x in found_list};matched=[];names={}
  for eid,x in found.items():
    name=str(x['canonical_name']);etype=str(x['entity_type']);entity=entities.setdefault(eid,{'id':eid,'canonical_name':name,'entity_type':etype,'aliases':list(x.get('aliases',[])),'country':name if etype=='country' else None,'region':None,'importance':0.,'mention_count':0,'evidence_ids':[]});discovered_ids.add(eid) if x.get('discovered') else None
    entity['aliases']=list(dict.fromkeys(entity['aliases']+list(x.get('aliases',[]))))
    if ev_id not in entity['evidence_ids']:entity['evidence_ids'].append(ev_id);entity['mention_count']+=1
    entity_evidence_scores.setdefault(eid,[]).append(ev_score);matched.append(eid);names[eid]=name
  for event_type in event_types[:3]:
   event_id=stable_id('evt',ev_id,event_type);actors,targets,locations=participant_roles(found,matched,names,event_type,text);event={'id':event_id,'event_type':event_type,'title':title,'timestamp':published,'location':names[locations[0]] if locations else None,'severity':0.,'confidence':0.,'entity_ids':matched,'evidence_ids':[ev_id],'actor_ids':actors,'target_ids':targets,'location_ids':locations,'action':action_for(event_type),'geopolitical_relevance':classify_geopolitical_relevance(text,event_type)};event['severity']=event_severity(event);event['confidence']=event_confidence(event,[ev]);event['strategic_relevance']=strategic_relevance(event);event['score']=event_score(event,[ev]);events[event_id]=event
   for eid in matched:entity_event_scores.setdefault(eid,[]).append(event['score'])
  kind=relation_type(text);positions=[]
  for eid in matched:
   m=re.search(r'(?<![a-z])'+re.escape(names[eid])+r'(?![a-z])',text,re.I)
   if m:positions.append((m.start(),eid))
  positions.sort()
  if kind!='mentioned_with' and len(positions)>=2:
   source_id,target_id=positions[0][1],positions[1][1];key=f'{source_id}|{kind}|{target_id}';rel=relationships.setdefault(key,{'source_entity_id':source_id,'relationship_type':kind,'target_entity_id':target_id,'confidence':.68,'weight':0.,'first_seen':published,'last_seen':published,'evidence_ids':[],'event_ids':[],'geopolitical_relevance':article_relevance});rel['last_seen']=published or rel['last_seen'];rel['confidence']=max(rel['confidence'],.76);rel['geopolitical_relevance']=max(rel['geopolitical_relevance'],article_relevance)
   if ev_id not in rel['evidence_ids']:rel['evidence_ids'].append(ev_id);rel['weight']+=1.
   for event_id,event in events.items():
    if event['evidence_ids']==[ev_id] and event_id not in rel['event_ids']:rel['event_ids'].append(event_id)
  for i,a in enumerate(matched):
   for b in matched[i+1:]:
    if a==b:continue
    pair=sorted((a,b));key=f'{pair[0]}|mentioned_with|{pair[1]}';semantic={f'{a}|{kind}|{b}',f'{b}|{kind}|{a}'}
    if kind!='mentioned_with' and any(k in relationships for k in semantic):continue
    rel=relationships.setdefault(key,{'source_entity_id':pair[0],'relationship_type':'mentioned_with','target_entity_id':pair[1],'confidence':.45,'weight':0.,'first_seen':published,'last_seen':published,'evidence_ids':[],'event_ids':[],'geopolitical_relevance':article_relevance});rel['last_seen']=published or rel['last_seen'];rel['geopolitical_relevance']=max(rel['geopolitical_relevance'],article_relevance)
    if ev_id not in rel['evidence_ids']:rel['evidence_ids'].append(ev_id);rel['weight']+=1.
 for eid,e in entities.items():e['importance']=entity_importance(e,entity_event_scores.get(eid),entity_evidence_scores.get(eid))
 for r in relationships.values():r['strength']=relationship_strength(r,[evidence_score(evidence[x]) for x in r['evidence_ids'] if x in evidence]);r['weight']=round(r['strength'],6)
 document['entities']=list(entities.values());document['events']=list(events.values());document['relationships']=list(relationships.values());document['evidence']=list(evidence.values());document['signals']=[];document['metadata'].update({'article_count':len(articles),'folded_duplicates':folded,'entity_count':len(entities),'event_count':len(events),'relationship_count':len(relationships),'semantic_relationship_count':sum(r['relationship_type']!='mentioned_with' for r in relationships.values()),'cooccurrence_relationship_count':sum(r['relationship_type']=='mentioned_with' for r in relationships.values()),'discovered_entity_count':len(discovered_ids),'event_participant_model':'actor-target-location-v4','strategic_attribution_model':'action-local-v1'})
 errors=validate_document(document)
 if errors:print(f"FAIL: canonical build produced {len(errors)} validation errors");[print(f" - {x}") for x in errors[:25]];return 1
 OUTPUT.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print(f"PASS: canonical v7 entities={len(entities)} events={len(events)} relationships={len(relationships)} evidence={len(evidence)} discovered={len(discovered_ids)}");return 0
if __name__=='__main__':raise SystemExit(main())
