#!/usr/bin/env python3
"""Collect near-real-time market indicators without requiring user API keys."""
from __future__ import annotations
import json
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone,time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent;SNAP=ROOT/'data'/'snapshot.json';UA='Mozilla/5.0 (compatible; GlobalPulse/13.2)'
WATCH=[('S&P 500','^GSPC','index','USD',2),('Dow Jones','^DJI','index','USD',2),('Nasdaq Composite','^IXIC','index','USD',2),('Nasdaq 100','^NDX','index','USD',2),('Russell 2000','^RUT','index','USD',2),('VIX','^VIX','volatility','USD',2),('WTI Crude','CL=F','commodity','USD',2),('Gold','GC=F','commodity','USD',2),('Bitcoin','BTC-USD','crypto','USD',0),('EUR / USD','EURUSD=X','fx','USD',4),('USD / JPY','JPY=X','fx','JPY',2),('U.S. 10Y Yield','^TNX','rates','%',2),('FTSE 100','^FTSE','index','GBP',2),('DAX','^GDAXI','index','EUR',2),('Nikkei 225','^N225','index','JPY',2),('Shanghai Composite','000001.SS','index','CNY',2),('Hang Seng','^HSI','index','HKD',2),('Nifty 50','^NSEI','index','INR',2),('Sensex','^BSESN','index','INR',2),('Apple','AAPL','equity','USD',2),('Microsoft','MSFT','equity','USD',2),('NVIDIA','NVDA','equity','USD',2),('Amazon','AMZN','equity','USD',2),('Alphabet','GOOGL','equity','USD',2),('Meta','META','equity','USD',2),('Tesla','TSLA','equity','USD',2)]
SESSIONS={'US':('America/New_York',time(9,30),time(16,0),time(4,0),time(20,0)),'UK':('Europe/London',time(8,0),time(16,30),time(7,0),time(17,30)),'DE':('Europe/Berlin',time(9,0),time(17,30),time(8,0),time(19,0)),'JP':('Asia/Tokyo',time(9,0),time(15,30),time(8,0),time(17,0)),'CN':('Asia/Shanghai',time(9,30),time(15,0),time(9,0),time(16,0)),'HK':('Asia/Hong_Kong',time(9,30),time(16,0),time(9,0),time(17,0)),'IN':('Asia/Kolkata',time(9,15),time(15,30),time(9,0),time(16,0))}
US={'^GSPC','^DJI','^IXIC','^NDX','^RUT','^VIX','AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','^TNX'};FUTURES={'CL=F','GC=F'};UK={'^FTSE'};DE={'^GDAXI'};JP={'^N225'};CN={'000001.SS'};HK={'^HSI'};IN={'^NSEI','^BSESN'};FX={'EURUSD=X','JPY=X'}
def now():return datetime.now(timezone.utc)
def session_for(symbol,kind):
 if symbol in FUTURES:return ('America/New_York',time(0,0),time(23,59),time(0,0),time(23,59))
 if symbol in US:return SESSIONS['US']
 if symbol in UK:return SESSIONS['UK']
 if symbol in DE:return SESSIONS['DE']
 if symbol in JP:return SESSIONS['JP']
 if symbol in CN:return SESSIONS['CN']
 if symbol in HK:return SESSIONS['HK']
 if symbol in IN:return SESSIONS['IN']
 return None
def session_status(symbol,kind,candle_ts,provider_state):
 current=now();age=max(0,(current-datetime.fromtimestamp(candle_ts,tz=timezone.utc)).total_seconds());fresh=age<=12*60
 if symbol=='BTC-USD':return 'live' if fresh else 'stale'
 if symbol in FX:
  local=current.astimezone(ZoneInfo('America/New_York'));open_fx=(local.weekday()<5 and not (local.weekday()==4 and local.time()>=time(17))) or (local.weekday()==6 and local.time()>=time(17));return 'live' if open_fx and fresh else ('stale' if open_fx else 'closed')
 session=session_for(symbol,kind)
 if not session:return 'stale' if fresh else 'closed'
 tz,regular_start,regular_end,extended_start,extended_end=session;local=current.astimezone(ZoneInfo(tz));lt=local.time()
 if local.weekday()>=5:return 'closed'
 if symbol in FUTURES:return 'live' if fresh else 'stale'
 if regular_start<=lt<regular_end:return 'live' if fresh else 'stale'
 if extended_start<=lt<extended_end:return 'live' if fresh else 'stale'
 return 'closed'
def fetch_quote(symbol,kind):
 last=None
 for host in ('query1.finance.yahoo.com','query2.finance.yahoo.com'):
  try:
   u=f'https://{host}/v8/finance/chart/{quote(symbol,safe="")}?range=1d&interval=1m&includePrePost=true&events=history';req=Request(u,headers={'User-Agent':UA,'Accept':'application/json'})
   with urlopen(req,timeout=10) as r:p=json.loads(r.read().decode())
   result=((p.get('chart') or {}).get('result') or [None])[0]
   if not result:raise RuntimeError('no chart result')
   meta=result.get('meta') or {};ts=result.get('timestamp') or [];q=((result.get('indicators') or {}).get('quote') or [{}])[0];cl=q.get('close') or [];pairs=[(int(t),float(v)) for t,v in zip(ts,cl) if v is not None]
   if not pairs:raise RuntimeError('no intraday candles')
   candle_ts,price=pairs[-1];previous=float(meta.get('chartPreviousClose') or meta.get('previousClose') or price);change=price-previous;pct=change/previous*100 if previous else 0;provider_state=str(meta.get('marketState') or '').upper();status=session_status(symbol,kind,candle_ts,provider_state);checked=now().isoformat()
   return {'price':price,'previousClose':previous,'change':change,'changePercent':pct,'marketTime':datetime.fromtimestamp(candle_ts,tz=timezone.utc).isoformat(),'marketState':provider_state,'sessionStatus':status,'currency':meta.get('currency'),'exchange':meta.get('fullExchangeName') or meta.get('exchangeName'),'endpoint':host,'interval':'1m','provider':'Yahoo Finance','quoteSource':'latest intraday candle','checkedAt':checked}
  except Exception as e:last=e
 raise RuntimeError(str(last) if last else 'all public market endpoints failed')
def collect(item):
 try:return item,fetch_quote(item[1],item[2]),None
 except Exception as e:return item,None,f'{type(e).__name__}: {e}'[:180]
def main():
 data=json.loads(SNAP.read_text(encoding='utf-8')) if SNAP.exists() else {};prev=data.get('marketData') if isinstance(data.get('marketData'),dict) else {};old={x.get('symbol'):x for x in prev.get('indicators',[]) if isinstance(x,dict)};vals={};errors=[]
 with ThreadPoolExecutor(max_workers=8) as pool:
  futures=[pool.submit(collect,x) for x in WATCH]
  for f in as_completed(futures):
   item,q,e=f.result();name,symbol,kind,unit,dec=item
   if q:q.update({'name':name,'symbol':symbol,'type':kind,'unit':unit,'decimals':dec,'status':q.get('sessionStatus','stale')});vals[symbol]=q
   elif symbol in old:
    x=dict(old[symbol]);x['status']='stale';x['lastAttemptedAt']=now().isoformat();vals[symbol]=x;errors.append({'symbol':symbol,'error':e})
   else:errors.append({'symbol':symbol,'error':e})
 indicators=[vals[s] for _,s,*_ in WATCH if s in vals]
 if not indicators:raise SystemExit(f'MARKET DATA REFRESH BLOCKED: all {len(WATCH)} public quotes failed; previous snapshot preserved')
 market={'updatedAt':now().isoformat(),'source':'Yahoo Finance public chart (1m)','provider':'Yahoo Finance','noApiKey':True,'quoteInterval':'1m','refreshMinutes':5,'sessionLogic':'exchange-local clock + fresh 1m candle; provider marketState is advisory only','indicators':indicators,'errors':errors,'liveCount':sum(x.get('status')=='live' for x in indicators),'closedCount':sum(x.get('status')=='closed' for x in indicators),'staleCount':sum(x.get('status')=='stale' for x in indicators)};data['marketData']=market;SNAP.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print(f"MARKET DATA: live={market['liveCount']} closed={market['closedCount']} stale={market['staleCount']} errors={len(errors)}")
if __name__=='__main__':main()
