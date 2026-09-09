#!/usr/bin/env python3
"""Build transparent source-quality and corroboration metrics.
No API key required. Domain diversity is treated as a proxy, not proof of
independence. Syndication, aggregators, social feeds and primary sources are
separated so raw article volume cannot masquerade as corroboration.
"""
from __future__ import annotations
import hashlib,json,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'

def load(name, default):
    try:return json.loads((DATA/name).read_text(encoding='utf-8'))
    except Exception:return default

def domain(url):
    try:return urlparse(str(url or '')).netloc.lower().removeprefix('www.')
    except Exception:return ''

def source_id(r):
    credit=r.get('credit') or {}
    if isinstance(credit,str):
        try:credit=json.loads(credit)
        except Exception:credit={}
    return str(credit.get('sourceId') or r.get('sourceLabel') or r.get('source_name') or r.get('source') or '')

def report_url(r):
    credit=r.get('credit') or {}
    if isinstance(credit,str):
        try:credit=json.loads(credit)
        except Exception:credit={}
    return str(r.get('original_link') or r.get('url') or r.get('link') or credit.get('url') or credit.get('sourceUrl') or '')

def identity(r):
    d=domain(report_url(r))
    return ('domain:'+d) if d else ('source:'+source_id(r))

def title_key(r):
    t=re.sub(r'[^a-z0-9 ]+',' ',str(r.get('title') or r.get('name') or '').lower())
    return re.sub(r'\s+',' ',t).strip()

def text(r):return ' '.join(str(r.get(k) or '') for k in ('title','name','summary','description')).strip()

# Conservative source classes. Unknown domains remain unknown rather than
# being granted trust automatically.
PRIMARY_DOMAINS={
    'un.org','nato.int','iaea.org','who.int','imf.org','worldbank.org',
    'state.gov','defense.gov','whitehouse.gov','congress.gov','europa.eu',
    'gov.uk','gov.uk','gov.ua','kremlin.ru','president.gov.ua',
    'mod.gov.uk','mod.gov.ua','canada.ca','australia.gov.au','gov.au',
    'gov.in','mofa.gov.sa','mofa.gov.ae','gov.il','gov.ir','gov.ng','gov.ke'
}
MAJOR_NEWS_DOMAINS={
    'reuters.com','apnews.com','bbc.com','bbc.co.uk','aljazeera.com','france24.com',
    'dw.com','ft.com','bloomberg.com','wsj.com','nytimes.com','washingtonpost.com',
    'theguardian.com','cnn.com','npr.org','pbs.org','cnbc.com','politico.com',
    'economist.com','abcnews.go.com','cbsnews.com','nbcnews.com','foxnews.com',
    'skynews.com','tass.com','xinhua.net','kyivindependent.com'
}
SPECIALIST_DOMAINS={
    'crisisgroup.org','acleddata.com','cfr.org','csis.org','iiss.org','sipri.org',
    'reliefweb.int','unhcr.org','ohchr.org','ecfr.eu','rusi.org','bellingcat.com'
}
AGGREGATOR_DOMAINS={
    'news.google.com','news.yahoo.com','yahoo.com','msn.com','aol.com','apple.news'
}
SOCIAL_DOMAINS={'x.com','twitter.com','facebook.com','instagram.com','tiktok.com','youtube.com','reddit.com','t.me'}
WIRE_HINTS={'reuters','associated press','ap news','afp','agency france presse','tass','xinhua'}

def source_class(d):
    if not d:return 'unknown'
    if d in PRIMARY_DOMAINS or d.endswith('.gov') or d.endswith('.gov.uk') or d.endswith('.mil'):
        return 'primary'
    if d in MAJOR_NEWS_DOMAINS:return 'major-news'
    if d in SPECIALIST_DOMAINS:return 'specialist'
    if d in AGGREGATOR_DOMAINS:return 'aggregator'
    if d in SOCIAL_DOMAINS:return 'social'
    return 'other'

def source_quality(d):
    c=source_class(d)
    return {'primary':100,'major-news':90,'specialist':82,'other':55,'aggregator':35,'social':20,'unknown':25}[c]

def independent_groups(reports):
    """Cluster near-identical headlines so copies do not count as corroboration."""
    groups=[]
    for r in reports:
        tokens=set(re.findall(r'[a-z0-9]{4,}',title_key(r)))
        if not tokens:continue
        placed=False
        for g in groups:
            gt=g['tokens']; j=len(tokens & gt)/max(1,len(tokens | gt))
            if j>=.82:
                g['reports'].append(r);g['tokens']|=tokens;placed=True;break
        if not placed:groups.append({'tokens':tokens,'reports':[r]})
    return groups

def main():
    snap=load('snapshot.json',{});breaking=load('breaking_news.json',{});events=load('live_events.json',{})
    reports=[x for x in (snap.get('stories') or snap.get('articles') or []) if isinstance(x,dict)]
    reports += [x for x in (breaking.get('articles') or []) if isinstance(x,dict)]
    unique={}
    for r in reports:
        u=report_url(r);key=u or hashlib.sha1(text(r).lower().encode()).hexdigest();unique[key]=r
    reports=list(unique.values());counts=Counter();by_identity=defaultdict(list)
    for r in reports:
        ident=identity(r)
        if ident:counts[ident]+=1;by_identity[ident].append(r)
    top=[]
    for ident,n in counts.most_common(40):
        d=ident.removeprefix('domain:') if ident.startswith('domain:') else ''
        top.append({'source':ident,'reportCount':n,'class':source_class(d),'quality':source_quality(d)})
    event_metrics=[]
    for e in (events.get('events') or [])[:80]:
        rs=[r for r in e.get('reports') or [] if isinstance(r,dict)]
        ids=[]; domains=[]; qualities=[]
        for r in rs:
            ident=identity(r)
            d=domain(report_url(r))
            if ident and ident not in ids:ids.append(ident)
            if d:domains.append(d);qualities.append(source_quality(d))
        groups=independent_groups(rs); independent=len(groups)
        unique_domains=sorted(set(domains)); domain_count=len(unique_domains)
        classes=Counter(source_class(d) for d in unique_domains)
        non_aggregating_domains=[d for d in unique_domains if source_class(d) not in {'aggregator','social'}]
        quality_avg=round(sum(qualities)/len(qualities)) if qualities else 0
        primary_count=classes.get('primary',0); major_count=classes.get('major-news',0)
        # Independence requires multiple reporting groups, not merely multiple URLs.
        if independent>=4 and len(non_aggregating_domains)>=4: independence='high'
        elif independent>=3 and len(non_aggregating_domains)>=3: independence='moderate-high'
        elif independent>=2 and len(non_aggregating_domains)>=2: independence='moderate'
        else: independence='low'
        concentration=max(Counter(domains).values(),default=0)/max(1,len(domains))
        wire_like=sum(1 for d in unique_domains if d.split('.')[0] in WIRE_HINTS or any(h in d for h in WIRE_HINTS))
        event_metrics.append({
            'eventId':e.get('id'),'title':e.get('title'),'reportCount':len(rs),
            'uniqueDomains':domain_count,'sourceIdentities':ids[:12],
            'independentReportingGroups':independent,'domains':unique_domains[:12],
            'domainClasses':dict(classes),'nonAggregatingDomains':len(non_aggregating_domains),
            'primarySourceDomains':primary_count,'majorNewsDomains':major_count,
            'wireLikeDomains':wire_like,'averageSourceQuality':quality_avg,
            'domainConcentration':round(concentration,3),'independence':independence,
            'note':'Near-identical headlines are grouped. Aggregators/social feeds are visible but do not count as strong independent corroboration. Domain diversity is a proxy, not proof.'
        })
    out={'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
         'method':'URL/domain diversity, conservative source classes, near-identical headline grouping and concentration controls. Source class is a monitoring aid, not a truth judgment.',
         'uniqueReportCount':len(reports),'uniqueSourceDomains':len({x.removeprefix('domain:') for x in counts if x.startswith('domain:')}),
         'sourceClassDefinitions':{'primary':'Government/institutional first-party domain. Does not make the claim true.','major-news':'Established news organization domain.','specialist':'Recognized research/humanitarian specialist.','other':'Unclassified publisher.','aggregator':'Republishing/aggregation surface; weak independence signal.','social':'Social platform; useful for leads, weak corroboration alone.','unknown':'No usable domain/source identity.'},
         'topSources':top,'eventSourceEvidence':event_metrics}
    (DATA/'source_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'SOURCE EVIDENCE: {len(reports)} reports / {out["uniqueSourceDomains"]} domains / quality metrics calculated')

if __name__=='__main__':main()
