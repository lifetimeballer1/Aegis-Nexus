#!/usr/bin/env python3
"""Build a compact, source-backed Intelligence Brain.

The visible graph is intentionally a small set of major hubs. Detailed records
are consolidated underneath those hubs so the UI can retain evidence without
turning every article, cartel, subgroup, or event into a graph node.
"""
from __future__ import annotations
import json,re
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=DATA/'intelligence_brain.json'
MAX_NODES=35
MAX_EVIDENCE_PER_ITEM=100

COUNTRIES={
 'United States':(38,-97),'China':(35.9,104.2),'Russia':(61.5,105.3),'Ukraine':(49,32),
 'Mexico':(23.6,-102.5),'Israel':(31,34.9),'Iran':(32.4,53.7),'India':(22.9,79),
 'North Korea':(40.3,127.5),'Taiwan':(23.7,120.9),'Turkey':(39,35.2),'Canada':(56.1,-106.3),
 'Colombia':(4.6,-74.1),'Brazil':(-10.8,-52.9),'Venezuela':(7.1,-66),
 'United Kingdom':(55.4,-3.4),'Germany':(51.2,10.5),'France':(46.2,2.2),
 'Saudi Arabia':(23.9,45.1),'Yemen':(15.6,48.5),'Syria':(35,38),'Iraq':(33.2,43.7),
 'Lebanon':(33.9,35.9),'Sudan':(12.9,30.2),'Somalia':(5.2,46.2),'Nigeria':(9.1,8.7),
 'Mali':(17.6,-4),'Niger':(17.6,8.1),'Burkina Faso':(12.4,-1.6),'Myanmar':(21.9,95.9),
 'Pakistan':(30.4,69.3),'Afghanistan':(33.9,67.7),'Japan':(36.2,138.3),'South Korea':(35.9,127.8)
}
CARTELS={
 'Sinaloa Cartel','CJNG','Jalisco New Generation Cartel','Gulf Cartel','Los Zetas','Northeast Cartel',
 'Santa Rosa de Lima Cartel','La Nueva Familia Michoacana','Juarez Cartel','Beltran Leyva Organization',
 'Clan del Golfo','Tren de Aragua','PCC','Primeiro Comando da Capital','Comando Vermelho','Los Choneros',
 'MS-13','Mara Salvatrucha'
}
ECONOMIC={
 'Oil':['oil','crude','brent','wti','petroleum','refinery','pipeline','opec','barrel','lng','natural gas','gas field','gasoline','diesel'],
 'Energy':['energy','electricity','power grid','nuclear','uranium','solar','wind power','coal','gas'],
 'Markets':['stock','stocks','market','markets','nasdaq','s&p 500','dow jones','bond','yield','currency','forex','bank','financial','vix','bitcoin','crypto'],
 'Trade & Supply Chains':['trade','tariff','export','import','sanction','customs','supply chain','logistics','shortage','disruption','manufacturing','semiconductor','chip supply'],
 'Food & Commodities':['food','grain','wheat','corn','maize','rice','soy','soybean','fertilizer','famine','hunger','food security','cattle','beef','commodity','commodities','lithium','cobalt','copper','nickel','rare earth','gold','iron ore','mining']
}
CONFLICTS={
 'Russia-Ukraine War':['ukraine','russia','zelensky','putin','donbas','crimea'],
 'Israel-Gaza War':['gaza','israel','hamas','palestinian','west bank'],
 'Sudan War':['sudan','rsf','rapid support forces','saf'],
 'Myanmar Conflict':['myanmar','burma','junta','resistance force'],
 'Sahel Conflicts':['mali','niger','burkina faso','sahel','jihadist']
}
CHOKEPOINTS={'Strategic Chokepoints':['hormuz','strait of hormuz','red sea','bab el-mandeb','houthi','suez canal','suez','panama canal']}
SOURCE_ARTIFACTS=['snapshot.json','breaking_news.json','live_articles.json','intelligence_graph.json','claims.json','intelligence_assessment.json','event_intelligence.json','event_market_impact.json','event_consistency.json','event_resolution.json','event_history.json','historical_trends.json','history.json','map_points.json','enforcer_maps.json']

STRATEGIC_ACTORS={'United States','China'}
STRATEGIC_ALIASES={
 'United States':('united states','u.s.','u.s.a.','usa','american','america','white house','pentagon','department of defense','defense department','state department','treasury','commerce department','justice department','congress'),
 'China':('china','chinese','people\'s republic of china','beijing','pla','people\'s liberation army','central military commission','state council','foreign ministry','commerce ministry','ccp','communist party of china')
}
ACTION_TERMS=('sanction','sanctions','sanctioned','military','strike','strikes','attack','attacked','deploy','deployed','deployment','tariff','tariffs','export control','export controls','trade restriction','trade restrictions','negotiat','agreement','treaty','diplomatic','cyber','hack','technology restriction','energy restriction','seized','arrested','indict','recognize','recognized','warned','threatened')
DOMAIN_TERMS=('military','defense','security','diplomatic','diplomacy','trade','tariff','economic','finance','technology','semiconductor','energy','oil','cyber','political','sanction')

def load(n,d=None):
    try:return json.loads((DATA/n).read_text(encoding='utf-8')) if (DATA/n).exists() else d
    except Exception:return d

def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values(): yield from walk(v)
    elif isinstance(obj,list):
        for v in obj: yield from walk(v)

def evidence(r):
    if not isinstance(r,dict): return None
    title=str(r.get('title') or r.get('name') or r.get('headline') or r.get('label') or '').strip()
    url=str(r.get('original_link') or r.get('url') or r.get('sourceUrl') or r.get('source_url') or r.get('link') or '').strip()
    source=str(r.get('sourceLabel') or r.get('source') or r.get('publisher') or r.get('provider') or '').strip()
    if not (title or url) or not (url or source): return None
    return {'title':title or 'Public intelligence record','url':url,'source':source or 'Public source','time':str(r.get('publishedAt') or r.get('published_date') or r.get('time') or r.get('updatedAt') or '')}

def evkey(x):return (str(x.get('title','')).lower(),str(x.get('url','')).lower(),str(x.get('source','')).lower())

def text(r):
    return ' '.join(str(r.get(k,'')) for k in ('title','headline','summary','description','content','detail','name','region','country','location','category','type','tags','keywords','eventType','layer','actor','actors','organization','organizations','group','provider','severity','impact','assessment','claim','text')).lower()

def slug(x):return re.sub(r'[^a-z0-9]+','-',str(x).lower()).strip('-')

def strategic_signal(t, actor):
    """Return evidence-weighted strategic signals for major-power prioritization.

    The score is intentionally modest: it should surface source-backed U.S./China
    activity, not manufacture prominence when a country is merely mentioned.
    """
    action_hits=sum(1 for term in ACTION_TERMS if term in t)
    domain_hits=sum(1 for term in DOMAIN_TERMS if term in t)
    aliases=STRATEGIC_ALIASES.get(actor,(actor.lower(),))
    # Require an actor-specific identity marker in the source; a generic action
    # term alone cannot manufacture a U.S./China strategic signal.
    if not any(re.search(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',t) for alias in aliases):
        return 0,0,0
    action=min(action_hits,6)
    domains=min(domain_hits,5)
    # Actor-specific strategic signal: a source that contains an action/domain
    # term gets more priority than a generic country co-mention.
    signal=action*3 + domains
    return signal,action,domains

def main():
    snap=load('snapshot.json',{}) or {}
    nodes={}; relationships=defaultdict(lambda:{'weight':0,'types':set(),'evidence':[]})
    reports=[]; artifact_counts={}

    def add(label,kind,source,score=1,meta=None):
        if not label or not source:return None
        i=slug(label)
        n=nodes.setdefault(i,{'id':i,'label':label,'kind':kind,'score':0,'mentions':0,'evidence':[]})
        n['score']+=score;n['mentions']+=1
        if meta:n.update(meta)
        key=evkey(source)
        if not any(evkey(x)==key for x in n['evidence']) and len(n['evidence']) < MAX_EVIDENCE_PER_ITEM:
            n['evidence'].append(source)
        return i

    def link(a,b,reason,source,typ):
        if not a or not b or a==b or not source:return
        k='|'.join(sorted((a,b)));r=relationships[k]
        r['weight']+=1;r['types'].add(typ)
        r['relationship']=reason
        if not any(evkey(x)==evkey(source) for x in r['evidence']) and len(r['evidence']) < MAX_EVIDENCE_PER_ITEM:
            r['evidence'].append(source)

    for filename in SOURCE_ARTIFACTS:
        obj=load(filename,None)
        if obj is None:continue
        rows=list(walk(obj));artifact_counts[filename]=len(rows)
        for r in rows:
            e=evidence(r)
            if e:reports.append((r,filename,e))

    market=snap.get('marketData') or {}
    market_sources=[]
    for q in market.get('indicators') or []:
        if isinstance(q,dict) and q.get('price') is not None:
            market_sources.append({'title':str(q.get('name') or q.get('symbol') or 'Market indicator'),'url':str(q.get('sourceUrl') or q.get('url') or ''),'source':str(q.get('source') or 'Public market feed'),'time':str(q.get('marketTime') or q.get('updatedAt') or '')})

    for r,typ,source in reports:
        t=text(r);hits=[]
        for country,(lat,lng) in COUNTRIES.items():
            if re.search(r'(?<![a-z])'+re.escape(country.lower())+r'(?![a-z])',t):
                extra=3
                strategic,action_hits,domain_hits=strategic_signal(t,country)
                if country in STRATEGIC_ACTORS:
                    extra += strategic
                meta={'country':country,'lat':lat,'lng':lng,'clusterKey':'country:'+country,'canonical':True}
                if country in STRATEGIC_ACTORS:
                    meta.update({'strategicActor':True,'strategicSignal':strategic,'actionSignals':action_hits,'domainSignals':domain_hits})
                hits.append(add(country,'country',source,extra,meta))
        if re.search(r'(?<![a-z])(?:u\.s\.?|u\.s\.?a\.?|usa|american)(?![a-z])',t):
            strategic,action_hits,domain_hits=strategic_signal(t,'united states')
            hits.append(add('United States','country',source,5+strategic,{'country':'United States','lat':38,'lng':-97,'clusterKey':'country:United States','canonical':True,'strategicActor':True,'strategicSignal':strategic,'actionSignals':action_hits,'domainSignals':domain_hits}))
        if any(re.search(r'(?<![a-z])'+re.escape(name.lower())+r'(?![a-z])',t) for name in CARTELS):
            hits.append(add('Cartels & Organized Crime','cartel',source,8,{'group':'Organized Crime','canonical':True,'lat':23.6,'lng':-102.5,'clusterKey':'cartel:organized-crime','description':'Consolidated hub for cartel, gang and organized-crime evidence; individual groups remain in node evidence, not as graph nodes.'}))
        for label,terms in CONFLICTS.items():
            if any(x in t for x in terms):hits.append(add(label,'conflict',source,5,{'group':'Major Conflict','canonical':True}))
        for label,terms in ECONOMIC.items():
            if any(x in t for x in terms):hits.append(add(label,'economic',source,3,{'group':'Economic Factor','canonical':True}))
        for label,terms in CHOKEPOINTS.items():
            if any(x in t for x in terms):hits.append(add(label,'chokepoint',source,3,{'group':'Strategic Infrastructure','canonical':True}))
        hits=[x for x in dict.fromkeys(hits) if x]
        for i,a in enumerate(hits):
            for b in hits[i+1:]:
                link(a,b,'These major hubs are co-mentioned in the same source-backed record; this is contextual evidence, not proof of causation.',source,typ)

    if market_sources:
        mid=add('Markets','economic',market_sources[0],4,{'group':'Economic Factor','canonical':True,'marketIndicators':len(market_sources)})
        for e in market_sources[1:]:
            if not any(evkey(x)==evkey(e) for x in nodes[mid]['evidence']) and len(nodes[mid]['evidence']) < MAX_EVIDENCE_PER_ITEM:
                nodes[mid]['evidence'].append(e)

    # Rank candidates by source-backed evidence first, then strategic action signal.
    # Major powers receive only an evidence-conditional bonus, so they cannot crowd
    # out an actor simply because its name appears in many unrelated records.
    def rank(n):
        evidence_count=len(n['evidence'])
        strategic=n.get('strategicSignal',0)
        action=n.get('actionSignals',0)
        domain=n.get('domainSignals',0)
        strategic_bonus=2 if n.get('strategicActor') and evidence_count and (action or strategic) else 0
        return (n['score'] + strategic_bonus, strategic, action, domain, evidence_count, n['mentions'])

    quotas={'country':8,'conflict':4,'economic':3,'cartel':1,'chokepoint':1}
    chosen=[]
    for kind in ('country','conflict','economic','cartel','chokepoint'):
        pool=[n for n in nodes.values() if n['kind']==kind]
        pool.sort(key=rank,reverse=True)
        chosen.extend(pool[:quotas[kind]])

    # Keep U.S./China available when they have meaningful source-backed strategic
    # evidence. If both qualify, they can displace the weakest country candidates.
    for required in ('United States','China'):
        rn=nodes.get(slug(required))
        qualifies=bool(rn and rn['evidence'] and (rn.get('actionSignals',0) or rn.get('strategicSignal',0)))
        if rn and qualifies and not any(n['id']==rn['id'] for n in chosen):
            idx=next((i for i in range(len(chosen)-1,-1,-1) if chosen[i]['kind']=='country' and chosen[i]['label'] not in ('United States','China')),None)
            if idx is not None:chosen[idx]=rn
            elif len(chosen)<MAX_NODES:chosen.append(rn)
    chosen=chosen[:MAX_NODES]
    keep={n['id'] for n in chosen}

    edges=[]
    for k,r in relationships.items():
        a,b=k.split('|',1)
        if a in keep and b in keep and r['evidence']:
            edges.append({'source':a,'target':b,'weight':r['weight'],'types':sorted(r['types']),'relationship':r['relationship'],'evidence':r['evidence'],'evidenceCount':len(r['evidence'])})
    edges.sort(key=lambda e:(e['evidenceCount'],e['weight']),reverse=True)

    now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    stats={'nodes':len(chosen),'edges':len(edges),'recordsScanned':len(reports),'artifactsScanned':len(artifact_counts),'artifactRows':artifact_counts,'marketIndicators':len(market.get('indicators') or []),'sourceBackedCandidates':len(nodes),'evidenceRecordsRetained':sum(len(n['evidence']) for n in chosen),'countryNodes':sum(n['kind']=='country' for n in chosen),'cartelNodes':sum(n['kind']=='cartel' for n in chosen),'conflictNodes':sum(n['kind']=='conflict' for n in chosen),'economicNodes':sum(n['kind']=='economic' for n in chosen),'chokepointNodes':sum(n['kind']=='chokepoint' for n in chosen),'strategicActorNodes':sum(bool(n.get('strategicActor')) for n in chosen),'strategicActorActionNodes':sum(bool(n.get('strategicActor') and n.get('actionSignals')) for n in chosen)}
    payload={'version':12,'updatedAt':now,'complete':True,'sourceBackedOnly':True,'consolidated':True,'maxNodes':MAX_NODES,'nodePolicy':'Major-hub graph. Country, conflict, economic and organized-crime records are consolidated beneath a bounded set of human-readable nodes. Evidence is retained on the hubs; subgroups such as Sinaloa and CJNG are evidence attributes, not separate graph nodes. Strategic actors receive only an evidence-conditional prioritization bonus when their records contain meaningful action/domain signals.','sourceArtifacts':SOURCE_ARTIFACTS,'method':'Consolidate the canonical news, conflict, OSINT map, event, claim, assessment, market-impact, historical and map-point artifacts into major hubs. Deduplicate evidence by title/url/source identity and cap each node/relationship at 100 retained evidence records. Prioritize source-backed strategic actor activity without hard-coding current geopolitical events.','caution':'Relationships are contextual evidence links and do not prove causation, coordination, intent or responsibility. Market links are context only.','nodes':chosen,'edges':edges,'stats':stats}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(f'INTELLIGENCE BRAIN: {len(chosen)} hubs / {len(edges)} relationships / {sum(len(n["evidence"]) for n in chosen)} retained evidence records / {len(reports)} source records scanned')

if __name__=='__main__':main()
