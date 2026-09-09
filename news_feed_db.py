#!/usr/bin/env python3
"""Persistent no-key news/X RSS collector for Global Pulse.

The collector uses the live source registry so every registered feed is actually
polled. A reachable feed with zero entries is recorded as online-empty rather
than silently looking healthy. For direct publisher feeds that return no entries,
a GDELT domain mirror is attempted so useful public reporting is not discarded
just because a publisher's RSS endpoint is sparse or temporarily incomplete.

Observed public-feed limits (documented 2026-09-09 live verification):
- GDELT Doc API (api.gdeltproject.org) rate-limits bursts with HTTP 429;
  parallel collectors must space GDELT requests (>=2.5s apart) and retry
  429/5xx with backoff instead of failing the source immediately.
- NPR topic feeds (feeds.npr.org) intermittently answer 404 on valid IDs;
  a single 404 must be retried before the source is marked failed.
- France 24 https://www.france24.com/en/rss now serves an HTML page, not RSS;
  HTML payloads are reported as a clean fetch error so quarantine mapping
  can replace them instead of surfacing an XML ParseError.
"""
from __future__ import annotations
import argparse,html,json,re,sqlite3,threading,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote,urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request,urlopen
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';DB_PATH=ROOT/'news_feed.db';JSON_PATH=DATA/'live_articles.json';STATUS_PATH=DATA/'live_status.json';POLL_SECONDS=300;RETENTION_DAYS=7;MAX_WORKERS=15;FETCH_TIMEOUT=12;GDELT_TIMEOUT=25;NPR_TIMEOUT=15;EXPORT_LIMIT=2000;USER_AGENT='GlobalPulse/13.0 (+https://github.com/lifetimeballer1/global-pulse)'
FETCH_RETRIES=3;RETRY_BACKOFF_SECONDS=(2.0,8.0,20.0);RETRYABLE_HTTP={429,500,502,503,504};GDELT_MIN_INTERVAL=2.5;_GDELT_LOCK=threading.Lock();_GDELT_LAST=[0.0]
BUILTIN_SOURCES={
'cnn':{'name':'CNN','url':'http://rss.cnn.com/rss/edition.rss','type':'news','category':'international'},'fox_politics':{'name':'Fox News Politics','url':'https://moxie.foxnews.com/google-publisher/politics.xml','type':'news','category':'us-politics','coverage':['united-states']},'npr_news':{'name':'NPR News','url':'https://feeds.npr.org/1001/rss.xml','type':'news','category':'us-politics','coverage':['united-states']},'bbc_world':{'name':'BBC World','url':'https://feeds.bbci.co.uk/news/world/rss.xml','type':'news','category':'international'},'guardian_world':{'name':'Guardian World','url':'https://www.theguardian.com/world/rss','type':'news','category':'international'},'al_jazeera':{'name':'Al Jazeera','url':'https://www.aljazeera.com/xml/rss/all.xml','type':'news','category':'international'},'dw_world':{'name':'DW World','url':'https://rss.dw.com/xml/rss-en-world','type':'news','category':'international'},'cna_world':{'name':'CNA World','url':'https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6311','type':'news','category':'international','coverage':['china']},'stars_stripes':{'name':'Stars and Stripes','url':'https://subscribe.stripes.com/rss/top-news.xml','type':'news','category':'security','coverage':['united-states']},'morse_audio':{'name':'Morse Report','url':'https://rss.buzzsprout.com/2637181.rss','type':'podcast','category':'us-politics','coverage':['united-states']},
'china_security':{'name':'Google News — China Security / PLA','url':'https://news.google.com/rss/search?q=China+PLA+military+Taiwan+South+China+Sea+security+when%3A1d&hl=en-US&gl=US&ceid=US:en','type':'china-security','category':'china-security','coverage':['china']},'china_economy':{'name':'Google News — China Economy / Trade','url':'https://news.google.com/rss/search?q=China+economy+trade+tariffs+exports+semiconductors+markets+when%3A1d&hl=en-US&gl=US&ceid=US:en','type':'china-economics','category':'china-economics','coverage':['china']},'china_politics':{'name':'Google News — China Politics / CCP','url':'https://news.google.com/rss/search?q=China+Xi+CCP+Communist+Party+government+policy+when%3A1d&hl=en-US&gl=US&ceid=US:en','type':'china-politics','category':'china-politics','coverage':['china']},'china_taiwan':{'name':'Google News — China Taiwan / Indo-Pacific','url':'https://news.google.com/rss/search?q=China+Taiwan+Indo-Pacific+Beijing+PLA+diplomacy+when%3A1d&hl=en-US&gl=US&ceid=US:en','type':'china-geopolitics','category':'china-geopolitics','coverage':['china']}}
X_ACCOUNTS={'NASA':'NASA','WhiteHouse':'White House','POTUS':'POTUS','NATO':'NATO','UN':'United Nations'}
def utc_now():return datetime.now(timezone.utc)
def iso_now():return utc_now().isoformat()
def clean(value,limit=700):
 value=html.unescape(value or '');value=re.sub(r'<script.*?</script>|<style.*?</style>',' ',value,flags=re.I|re.S);value=re.sub(r'<[^>]+>',' ',value);return re.sub(r'\s+',' ',value).strip()[:limit]
def parse_date(value):
 if not value:return iso_now()
 try:dt=parsedate_to_datetime(value)
 except Exception:
  try:dt=datetime.fromisoformat(value.replace('Z','+00:00'))
  except Exception:return iso_now()
 if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
 return dt.astimezone(timezone.utc).isoformat()
def node_text(node,*tags):
 RSS1='{http://purl.org/rss/1.0/}'
 for tag in tags:
  variants=(tag,) if tag.startswith('{') else (tag,RSS1+tag)
  for variant in variants:
   try:found=node.find(variant)
   except SyntaxError:continue
   if found is not None:
    if found.text:return found.text.strip()
    if found.attrib.get('href'):return found.attrib['href'].strip()
 return ''
def node_link(node):
 link=node_text(node,'link','{http://www.w3.org/2005/Atom}link')
 if link:return link
 for child in node:
  if child.tag.endswith('link') and child.attrib.get('href'):return child.attrib['href'].strip()
 return ''
def parse_feed(payload,source_id,meta):
 head=bytes(payload[:256]).strip().lower() if isinstance(payload,(bytes,bytearray)) else str(payload[:256]).strip().lower()
 if head.startswith(b'<!doctype html') or head.startswith(b'<html'):
  raise ValueError(f"publisher returned HTML page, not RSS (quarantine candidate): {meta['name']}")
 root=ET.fromstring(payload);items=root.findall('.//item');atom=False
 if not items:items=root.findall('.//{http://purl.org/rss/1.0/}item')
 if not items:items=root.findall('.//{http://www.w3.org/2005/Atom}entry');atom=True
 rows=[]
 for item in items[:100]:
  title=clean(node_text(item,'title','{http://www.w3.org/2005/Atom}title'),300);link=node_link(item);summary=clean(node_text(item,'description','summary','content','{http://www.w3.org/2005/Atom}summary','{http://www.w3.org/2005/Atom}content'),900);pub=node_text(item,'pubDate','published','updated','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated');author=clean(node_text(item,'author','{http://purl.org/dc/elements/1.1/}creator','{http://www.w3.org/2005/Atom}author'),160)
  if not link:continue
  if not title:title=f"Update from {meta['name']}"
  rows.append({'url':link,'title':title,'published_date':parse_date(pub),'summary_snippet':summary,'source_name':meta['name'],'source_type':meta.get('type','news'),'category':meta.get('category','general'),'author':author,'username':'','credit_metadata':json.dumps({'sourceId':source_id,'sourceUrl':meta['url'],'feedFormat':'atom' if atom else 'rss'},ensure_ascii=False)})
 return rows
def _polite_gdelt_wait():
 with _GDELT_LOCK:
  wait=GDELT_MIN_INTERVAL-(time.monotonic()-_GDELT_LAST[0])
  if wait>0:time.sleep(wait)
  _GDELT_LAST[0]=time.monotonic()
def _timeout_for(url):
 if 'api.gdeltproject.org' in url:return GDELT_TIMEOUT
 if 'feeds.npr.org' in url:return NPR_TIMEOUT
 return FETCH_TIMEOUT
def fetch(url,timeout=None):
 if timeout is None:timeout=_timeout_for(url)
 req=Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8'})
 last=None
 for attempt in range(1+FETCH_RETRIES):
  if 'api.gdeltproject.org' in url:_polite_gdelt_wait()
  try:
   with urlopen(req,timeout=timeout) as response:return response.read()
  except HTTPError as exc:
   last=exc
   if int(exc.code or 0) not in RETRYABLE_HTTP or attempt>=FETCH_RETRIES:raise
  except (URLError,TimeoutError,ConnectionError,OSError) as exc:
   last=exc
   if attempt>=FETCH_RETRIES:raise
  time.sleep(RETRY_BACKOFF_SECONDS[min(attempt,len(RETRY_BACKOFF_SECONDS)-1)])
 raise RuntimeError(f'fetch retries exhausted: {last}' if last else 'fetch retries exhausted')
def x_urls(handle):return [f'https://rss.xcancel.com/{handle}/rss',f'https://xcancel.com/{handle}/rss']
def parse_x_account(handle,display_name):
 last=None
 for url in x_urls(handle):
  try:
   payload=fetch(url);text=payload.decode('utf-8',errors='ignore')
   if 'RSS reader not yet whitelisted' in text or 'checking your browser' in text.lower():raise RuntimeError('proxy challenge/whitelist response')
   rows=parse_feed(payload,f'x:{handle}',{'name':f'X @{handle}','type':'social','category':'osint','url':url})
   for row in rows:row['username']=handle;row['credit_metadata']=json.dumps({'sourceId':f'x:{handle}','handle':handle,'displayName':display_name,'proxy':url},ensure_ascii=False)
   return rows
  except Exception as exc:last=exc
 raise RuntimeError(str(last) if last else 'X proxy unavailable')
def load_sources():
 result={};registry=DATA/'sources.json'
 try:
  doc=json.loads(registry.read_text(encoding='utf-8'))
  for i,item in enumerate(doc.get('feeds',[])):
   if not isinstance(item,dict) or not item.get('url') or not item.get('name'):continue
   key=re.sub(r'[^a-z0-9]+','_',str(item['name']).lower()).strip('_') or f'feed_{i}';base=key;n=2
   while key in result:key=f'{base}_{n}';n+=1
   result[key]={'name':str(item['name']),'url':str(item['url']),'type':str(item.get('type') or 'news'),'category':str(item.get('category') or item.get('type') or 'general'),'coverage':list(item.get('coverage') or [])}
 except Exception as exc:print(f'SOURCE REGISTRY WARNING: {type(exc).__name__}: {exc}; using built-in safety sources')
 for key,meta in BUILTIN_SOURCES.items():result.setdefault(key,meta)
 return result
def is_aggregator(url):
 host=urlparse(url).netloc.lower();return any(x in host for x in ('news.google.com','api.gdeltproject.org'))
def domain_mirror_url(meta):
 host=urlparse(meta['url']).netloc.lower().split(':')[0]
 if not host or is_aggregator(meta['url']) or host.startswith('feeds.') or host.startswith('rss.') or host.startswith('subscribe.'):return None
 query=quote(f'domain:{host}',safe='');return f'https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=ArtList&format=rss&maxrecords=75&timespan=24h&sort=datedesc'
def fetch_news_source(source_id,meta):
 try:
  rows=parse_feed(fetch(meta['url']),source_id,meta)
  if rows:return rows,None,{'mode':'native','httpOk':True,'rowsFetched':len(rows),'empty':False}
  mirror=domain_mirror_url(meta)
  if mirror:
   try:
    fallback_meta=dict(meta);fallback_meta['url']=mirror;rows=parse_feed(fetch(mirror),source_id,fallback_meta)
    for row in rows:
     row['source_name']=meta['name'];row['source_type']=meta.get('type','news');row['category']=meta.get('category','general');row['credit_metadata']=json.dumps({'sourceId':source_id,'sourceUrl':meta['url'],'fallback':'GDELT domain mirror','fallbackUrl':mirror,'originalSource':meta['name']},ensure_ascii=False)
    if rows:return rows,None,{'mode':'gdelt-domain-fallback','httpOk':True,'rowsFetched':len(rows),'empty':False}
   except Exception as fallback_exc:return [],{'source':meta['name'],'error':f'empty native feed; GDELT fallback failed: {type(fallback_exc).__name__}: {fallback_exc}'[:240]},{'mode':'online-empty','httpOk':True,'rowsFetched':0,'empty':True}
  return [],None,{'mode':'online-empty','httpOk':True,'rowsFetched':0,'empty':True}
 except Exception as exc:return [],{'source':meta['name'],'error':f'{type(exc).__name__}: {exc}'[:240]},{'mode':'failed','httpOk':False,'rowsFetched':0,'empty':False}
def fetch_x_source(handle,display_name):
 try:rows=parse_x_account(handle,display_name);return rows,None,{'mode':'native','httpOk':True,'rowsFetched':len(rows),'empty':not bool(rows)}
 except Exception as exc:return [],{'source':f'X @{handle}','error':f'{type(exc).__name__}: {exc}'[:240]},{'mode':'failed','httpOk':False,'rowsFetched':0,'empty':False}
def init_db(conn):
 conn.execute('PRAGMA journal_mode=WAL');conn.execute('PRAGMA busy_timeout=5000');conn.execute('CREATE TABLE IF NOT EXISTS articles (url TEXT PRIMARY KEY,title TEXT NOT NULL,published_date TEXT NOT NULL,summary_snippet TEXT DEFAULT \'\',source_name TEXT NOT NULL,source_type TEXT NOT NULL,category TEXT DEFAULT \'general\',author TEXT DEFAULT \'\',username TEXT DEFAULT \'\',credit_metadata TEXT DEFAULT \'{}\',fetched_at TEXT NOT NULL)');conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_date DESC)');conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_name)');conn.commit()
def purge_old(conn):
 cutoff=(utc_now()-timedelta(days=RETENTION_DAYS)).isoformat();cur=conn.execute('DELETE FROM articles WHERE published_date < ?',(cutoff,));conn.commit();return cur.rowcount
def upsert_articles(conn,rows):
 added=0;now=iso_now()
 for row in rows:
  try:
   cur=conn.execute('INSERT OR IGNORE INTO articles (url,title,published_date,summary_snippet,source_name,source_type,category,author,username,credit_metadata,fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(row['url'],row['title'],row['published_date'],row['summary_snippet'],row['source_name'],row['source_type'],row['category'],row['author'],row['username'],row['credit_metadata'],now));added+=1 if cur.rowcount else 0
  except sqlite3.Error:continue
 conn.commit();return added
def export_json(conn,limit=EXPORT_LIMIT):
 rows=conn.execute('SELECT url,title,published_date,summary_snippet,source_name,source_type,category,author,username,credit_metadata FROM articles ORDER BY datetime(published_date) DESC LIMIT ?',(limit,)).fetchall();articles=[]
 for r in rows:
  try:credit=json.loads(r[9] or '{}')
  except Exception:credit={'raw':r[9]}
  articles.append({'url':r[0],'title':r[1],'published_date':r[2],'summary_snippet':r[3],'source':r[4],'sourceType':r[5],'category':r[6],'author':r[7],'username':r[8],'credit':credit})
 return json.dumps({'updatedAt':iso_now(),'retentionDays':RETENTION_DAYS,'count':len(articles),'exportLimit':EXPORT_LIMIT,'articles':articles},ensure_ascii=False,indent=2)+'\n'
def write_export(conn):DATA.mkdir(exist_ok=True);JSON_PATH.write_text(export_json(conn),encoding='utf-8',newline='\n')
def restore_published_articles(conn):
 """Recover retained source records after a cache miss, not current feed health."""
 if conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0] or not JSON_PATH.exists():
  return 0
 document=json.loads(JSON_PATH.read_text(encoding='utf-8'))
 rows=[];now=utc_now();cutoff=now-timedelta(days=RETENTION_DAYS)
 for article in document.get('articles',[]):
  if not isinstance(article,dict):continue
  if not all(isinstance(article.get(k),str) and article[k].strip() for k in ('url','title','source','published_date')):continue
  if not article['url'].startswith(('https://','http://')):continue
  try:
   stamp=datetime.fromisoformat(article['published_date'].replace('Z','+00:00'))
   if stamp.tzinfo is None or not cutoff<=stamp<=now:continue
  except ValueError:continue
  rows.append({'url':article['url'],'title':article['title'],'published_date':article['published_date'],
   'summary_snippet':article.get('summary_snippet') or '', 'source_name':article['source'],
   'source_type':article.get('sourceType') or 'news','category':article.get('category') or 'general',
   'author':article.get('author') or '', 'username':article.get('username') or '',
   'credit_metadata':json.dumps(article.get('credit') or {},ensure_ascii=False)})
 return upsert_articles(conn,rows)

def run_cycle(conn):
 sources=load_sources();fetched_rows=[];errors=[];source_results=[];jobs=[]
 with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
  for source_id,meta in sources.items():jobs.append((source_id,meta,pool.submit(fetch_news_source,source_id,meta)))
  for handle,name in X_ACCOUNTS.items():jobs.append((f'x:{handle}',{'name':f'X @{handle}','type':'social','category':'osint','coverage':[],'url':''},pool.submit(fetch_x_source,handle,name)))
  for source_id,meta,future in jobs:
   try:
    rows,error,telemetry=future.result();fetched_rows.extend(rows);result={'sourceId':source_id,'name':meta['name'],'type':meta.get('type','news'),'category':meta.get('category','general'),'coverage':meta.get('coverage',[]),'rowsFetched':len(rows),'httpOk':bool(telemetry.get('httpOk')),'mode':telemetry.get('mode'),'emptyFeed':bool(telemetry.get('empty')),'error':(error or {}).get('error','')};source_results.append(result)
    if error:errors.append(error)
   except Exception as exc:
    result={'sourceId':source_id,'name':meta['name'],'type':meta.get('type','news'),'category':meta.get('category','general'),'coverage':meta.get('coverage',[]),'rowsFetched':0,'httpOk':False,'mode':'failed','emptyFeed':False,'error':f'{type(exc).__name__}: {exc}'[:240]};source_results.append(result);errors.append({'source':meta['name'],'error':result['error']})
 purged=purge_old(conn);added=upsert_articles(conn,fetched_rows);write_export(conn);count=conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0];healthy=sum(1 for x in source_results if x['httpOk']);empty=sum(1 for x in source_results if x['httpOk'] and x['emptyFeed']);fallback=sum(1 for x in source_results if x['mode']=='gdelt-domain-fallback');total=len(source_results)
 status={'updatedAt':iso_now(),'feedsChecked':total,'rowsFetched':len(fetched_rows),'newArticles':added,'purged':purged,'databaseArticles':count,'exportedArticles':min(count,EXPORT_LIMIT),'exportLimit':EXPORT_LIMIT,'healthySources':healthy,'emptySources':empty,'fallbackSources':fallback,'failedSources':errors,'sourceResults':source_results,'pollSeconds':POLL_SECONDS,'retentionDays':RETENTION_DAYS,'fetchTimeoutSeconds':FETCH_TIMEOUT}
 STATUS_PATH.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');return status
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args();DATA.mkdir(exist_ok=True);conn=sqlite3.connect(DB_PATH)
 try:
  init_db(conn)
  restored=restore_published_articles(conn)
  if restored:print(f'Restored {restored} retained published articles after database cache miss')
  while True:
   try:status=run_cycle(conn);print(json.dumps({'feedsChecked':status['feedsChecked'],'rowsFetched':status['rowsFetched'],'newArticles':status['newArticles'],'healthySources':status['healthySources'],'emptySources':status['emptySources'],'fallbackSources':status['fallbackSources'],'failedSources':len(status['failedSources']),'exportedArticles':status['exportedArticles']},ensure_ascii=False))
   except Exception as exc:print(f'collector-cycle-error: {type(exc).__name__}: {exc}')
   if args.once:break
   time.sleep(POLL_SECONDS)
 finally:conn.close()
if __name__=='__main__':main()
