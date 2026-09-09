#!/usr/bin/env python3
"""Connect live events to relevant market indicators without claiming causation."""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
DATA=Path(__file__).resolve().parent/'data'
WATCH={'energy':{'WTI Crude','Gold'},'risk':{'VIX','Gold','U.S. 10Y Yield'},'europe':{'FTSE 100','DAX','EUR / USD'},'asia':{'Nikkei 225','Shanghai Composite','Hang Seng','Nifty 50','Sensex','USD / JPY'},'us':{'S&P 500','Dow Jones','Nasdaq Composite','Nasdaq 100','Russell 2000','U.S. 10Y Yield'},'crypto':{'Bitcoin'}}
def load(n,d):
 try:return json.loads((DATA/n).read_text(encoding='utf-8'))
 except:return d
def buckets(title):
 t=str(title or '').lower();b=set()
 if re.search(r'oil|crude|energy|shipping|hormuz|red sea|gulf|sanction|supply',t):b.add('energy')
 if re.search(r'war|attack|missile|drone|invasion|strike|military|conflict|coup|escalat',t):b.add('risk')
 if re.search(r'russia|ukraine|europe|uk|britain|france|germany|nato',t):b.add('europe')
 if re.search(r'us|america|trump|white house|fed|congress',t):b.add('us')
 if re.search(r'china|taiwan|japan|korea|india|asia',t):b.add('asia')
 if re.search(r'bitcoin|crypto',t):b.add('crypto')
 return b or {'risk'}
def main():
 ev=load('live_events.json',{});snap=load('snapshot.json',{});market=snap.get('marketData') or {};inds={x.get('name'):x for x in market.get('indicators',[]) if isinstance(x,dict)};out=[]
 for e in ev.get('events',[])[:40]:
  b=buckets(e.get('title'));names=[]
  for k in b:
   for n in WATCH.get(k,set()):
    if n in inds and n not in names:names.append(n)
  related=[{'name':n,'price':inds[n].get('price'),'changePercent':inds[n].get('changePercent'),'status':inds[n].get('status'),'marketTime':inds[n].get('marketTime')} for n in names[:8]]
  out.append({'eventId':e.get('id'),'title':e.get('title'),'marketBuckets':sorted(b),'relatedIndicators':related,'interpretation':'Contextual market exposure only. Price moves are not attributed to this event unless independently established.','updatedAt':market.get('updatedAt')})
 payload={'version':1,'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'method':'Keyword-based event-to-market relevance mapping using existing public market indicators; no causal attribution.','events':out}
 (DATA/'event_market_impact.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print('EVENT MARKET IMPACT:',len(out),'events mapped')
if __name__=='__main__':main()
