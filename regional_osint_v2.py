#!/usr/bin/env python3
"""Robust regional OSINT collector with correct GDELT FIPS codes and failover."""
# Coverage is intentionally independent of the 5-minute news snapshot writer;
# its output is preserved by update_snapshot_fast.py and published separately.
import hashlib,json,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent; SNAP=ROOT/'data'/'snapshot.json'; UA='GlobalPulse/5.0 (+https://github.com/lifetimeballer1/global-pulse)'
REGIONS={'Africa':['MA','DZ','TN','LY','EG','SD','SS','CD','NG','SO','ET','KE','MZ','CM','CF','CG','GA','MR','ML','BF','NE','TD','TZ','UG','ZA','AO','SN','GH','GM','GN','SL','LR','CI','ER','DJ','RW','BI','ZW','ZM','NA','BW','MW','LS'],'South America':['BR','CO','VE','EC','PE','BO','PY','UY','AR','CL','GY','SR'],'South Asia':['IN','PK','BD','AF','LK','NP','BT','MV','MM']}
NAMES={'MA':'Morocco','DZ':'Algeria','TN':'Tunisia','LY':'Libya','EG':'Egypt','SD':'Sudan','SS':'South Sudan','CD':'DR Congo','NG':'Nigeria','SO':'Somalia','ET':'Ethiopia','KE':'Kenya','MZ':'Mozambique','CM':'Cameroon','CF':'Central African Republic','CG':'Republic of the Congo','GA':'Gabon','MR':'Mauritania','ML':'Mali','BF':'Burkina Faso','NE':'Niger','TD':'Chad','TZ':'Tanzania','UG':'Uganda','ZA':'South Africa','AO':'Angola','SN':'Senegal','GH':'Ghana','GM':'Gambia','GN':'Guinea','SL':'Sierra Leone','LR':'Liberia','CI':"Cote d'Ivoire",'ER':'Eritrea','DJ':'Djibouti','RW':'Rwanda','BI':'Burundi','ZW':'Zimbabwe','ZM':'Zambia','NA':'Namibia','BW':'Botswana','MW':'Malawi','LS':'Lesotho','BR':'Brazil','CO':'Colombia','VE':'Venezuela','EC':'Ecuador','PE':'Peru','BO':'Bolivia','PY':'Paraguay','UY':'Uruguay','AR':'Argentina','CL':'Chile','GY':'Guyana','SR':'Suriname','IN':'India','PK':'Pakistan','BD':'Bangladesh','AF':'Afghanistan','LK':'Sri Lanka','NP':'Nepal','BT':'Bhutan','MV':'Maldives','MM':'Myanmar'}
FIPS={'MA':'MO','DZ':'AG','TN':'TS','LY':'LY','EG':'EG','SD':'SU','SS':'OD','CD':'CG','NG':'NI','SO':'SO','ET':'ET','KE':'KE','MZ':'MZ','CM':'CM','CF':'CT','CG':'CF','GA':'GB','MR':'MR','ML':'ML','BF':'UV','NE':'NG','TD':'CD','TZ':'TZ','UG':'UG','ZA':'SF','AO':'AO','SN':'SG','GH':'GH','GM':'GA','GN':'GV','SL':'SL','LR':'LI','CI':'IV','ER':'ER','DJ':'DJ','RW':'RW','BI':'BY','ZW':'ZI','ZM':'ZA','NA':'WA','BW':'BC','MW':'MI','LS':'LT','BR':'BR','CO':'CO','VE':'VE','EC':'EC','PE':'PE','BO':'BL','PY':'PA','UY':'UY','AR':'AR','CL':'CI','GY':'GY','SR':'NS','IN':'IN','PK':'PK','BD':'BG','AF':'AF','LK':'CE','NP':'NP','BT':'BT','MV':'MV','MM':'BM'}
CENTERS={'MA':(31.79,-7.09),'DZ':(28.03,1.66),'TN':(33.89,9.56),'LY':(26.34,17.23),'EG':(26.82,30.80),'SD':(15.50,32.56),'SS':(4.85,31.58),'CD':(-2.88,23.66),'NG':(9.08,7.40),'SO':(5.15,46.20),'ET':(9.15,40.49),'KE':(0.02,37.91),'MZ':(-18.67,35.53),'CM':(5.96,10.15),'CF':(6.61,20.94),'CG':(-0.23,15.83),'GA':(-0.80,11.61),'MR':(20.25,-10.94),'ML':(17.57,-4.00),'BF':(12.24,-1.56),'NE':(17.61,8.08),'TD':(15.45,18.73),'TZ':(-6.37,34.89),'UG':(1.37,32.29),'ZA':(-30.56,22.94),'AO':(-11.20,17.87),'SN':(14.50,-14.45),'GH':(7.95,-1.02),'GM':(13.44,-15.31),'GN':(9.95,-9.70),'SL':(8.46,-11.78),'LR':(6.43,-9.43),'CI':(7.54,-5.55),'ER':(15.18,39.78),'DJ':(11.83,42.59),'RW':(-1.94,29.87),'BI':(-3.37,29.92),'ZW':(-19.02,29.15),'ZM':(-13.13,27.85),'NA':(-22.56,17.07),'BW':(-22.33,24.68),'MW':(-13.25,34.30),'LS':(-29.61,28.23),'BR':(-14.24,-51.93),'CO':(4.57,-74.30),'VE':(6.42,-66.59),'EC':(-1.83,-78.18),'PE':(-9.19,-75.02),'BO':(-16.29,-63.59),'PY':(-23.44,-58.44),'UY':(-32.52,-55.77),'AR':(-38.42,-63.62),'CL':(-35.68,-71.54),'GY':(4.86,-58.93),'SR':(3.92,-56.03),'IN':(22.35,78.67),'PK':(30.38,69.35),'BD':(23.68,90.36),'AF':(33.94,67.71),'LK':(7.87,80.77),'NP':(28.39,84.12),'BT':(27.51,90.43),'MV':(3.20,73.22),'MM':(21.92,95.96)}
TERMS='(conflict OR attack OR fighting OR bombing OR shooting OR insurgent OR militant OR violence OR clash OR kidnapping OR military OR protest)'
def now(): return datetime.now(timezone.utc).isoformat()
def stable_id(prefix,cc,lat,lng,url,title): return f"{prefix}-{cc}-{hashlib.sha1(f'{prefix}|{cc}|{lat:.5f}|{lng:.5f}|{url}|{title}'.encode()).hexdigest()[:16]}"
def fetch(url,timeout=10):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json,application/xml,text/xml,*/*'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
def gdelt(region,cc,geores):
 q=urllib.parse.quote(f'locationcc:{FIPS[cc]} {TERMS}',safe='')
 url=f'https://api.gdeltproject.org/api/v2/geo/geo?query={q}&mode=PointData&format=GeoJSON&timespan=24h&maxrecords=80&geores={geores}'
 try:
  obj=json.loads(fetch(url).decode('utf-8','replace')); out=[]
  for f in obj.get('features',[]):
   c=(f.get('geometry') or {}).get('coordinates') or []
   if len(c)<2: continue
   lng,lat=float(c[0]),float(c[1]); p=f.get('properties') or {}; u=str(p.get('url') or p.get('oneurl') or p.get('sourceurl') or '').strip(); title=str(p.get('name') or NAMES[cc]).strip()[:180]
   if not (-90<=lat<=90 and -180<=lng<=180): continue
   resolution='CITY/LANDMARK' if geores==2 else 'ADM1/CITY'
   out.append({'id':stable_id('gdelt',cc,lat,lng,u,title),'lat':lat,'lng':lng,'title':title,'detail':f'Fresh GDELT GEO {resolution} signal','url':u,'sourceUrl':u,'source':'GDELT GEO','sourceDomain':(urlparse(u).hostname or '').lower().removeprefix('www.'),'eventType':'OSINT/GEO','layer':'osint-regional','region':region,'country':NAMES[cc],'countryCode':cc,'fipsCountryCode':FIPS[cc],'geoResolution':resolution,'confidence':'DISCOVERY SIGNAL','observedAt':p.get('seendate') or now(),'imageUrl':str(p.get('sharingimage') or p.get('image') or '').strip() or None})
  return out,None
 except Exception as e:return [],str(e)[:180]
def rss(region,cc):
 name=NAMES[cc]; q=urllib.parse.quote(f'"{name}" (conflict OR fighting OR attack OR military OR protest) when:1d')
 try:
  root=ET.fromstring(fetch(f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'));out=[];lat,lng=CENTERS[cc]
  for it in root.findall('./channel/item')[:10]:
   title=(it.findtext('title') or '').strip();u=(it.findtext('link') or '').strip();pub=(it.findtext('pubDate') or '').strip()
   if u: out.append({'id':stable_id('rss',cc,lat,lng,u,title),'lat':lat,'lng':lng,'title':title[:180],'detail':'Current regional report; country-center coordinate because no precise GDELT point was available','url':u,'sourceUrl':u,'source':'Google News RSS','sourceDomain':(urlparse(u).hostname or '').lower().removeprefix('www.'),'layer':'osint-regional','type':'reported-area','eventType':'REPORTED AREA','region':region,'country':name,'countryCode':cc,'fipsCountryCode':FIPS[cc],'geoResolution':'COUNTRY-CENTER-APPROXIMATE','confidence':'OSINT REPORT','observedAt':pub or now(),'imageUrl':None})
  return out,None
 except Exception as e:return [],str(e)[:180]
def main():
 snap=json.loads(SNAP.read_text(encoding='utf-8'));base=[m for m in snap.get('markers',[]) if m.get('layer')!='osint-regional'];points=[];counts={r:0 for r in REGIONS};precise={r:0 for r in REGIONS};failed=[]
 with ThreadPoolExecutor(max_workers=24) as pool:
  first={(r,cc):pool.submit(gdelt,r,cc,2) for r,codes in REGIONS.items() for cc in codes}
  no_city=[]
  for (r,cc),f in first.items():
   pts,e=f.result()
   if pts: points.extend(pts);counts[r]+=len(pts);precise[r]+=len(pts)
   else:no_city.append((r,cc,e or 'no city/landmark results'))
  second={(r,cc):pool.submit(gdelt,r,cc,1) for r,cc,_ in no_city}; no_gdelt=[]
  for (r,cc),f in second.items():
   pts,e=f.result()
   if pts: points.extend(pts);counts[r]+=len(pts)
   else:no_gdelt.append((r,cc,e or 'no ADM1/city results'))
  third={(r,cc):pool.submit(rss,r,cc) for r,cc,_ in no_gdelt}
  for (r,cc),f in third.items():
   pts,e=f.result()
   if pts: points.extend(pts);counts[r]+=len(pts)
   else: failed.append({'region':r,'country':NAMES[cc],'countryCode':cc,'error':str(e or 'no results')[:180]})
 seen=set();clean=[]
 for p in points:
  k=(p.get('source'),p.get('sourceUrl') or p.get('url'),round(float(p['lat']),4),round(float(p['lng']),4))
  if k not in seen:seen.add(k);clean.append(p)
 clean.sort(key=lambda p:p.get('geoResolution')=='COUNTRY-CENTER-APPROXIMATE')
 snap['markers']=base+clean[:2500];o=snap.setdefault('osintMaps',{});o['version']=4;o['regionalPoints']=clean;o['regionalCounts']=counts;o['regionalPreciseCounts']=precise;o['regionalFailures']=failed;o['regionalUpdatedAt']=now();o['regionalSourcePolicy']='GDELT GEO FIPS queries: city/landmark first, ADM1/city second; Google News RSS country-center fallback only after both GDELT passes fail.';o['regionalFipsQueryPolicy']='GDELT locationcc requires FIPS 10-4; countryCode remains ISO-style.'
 SNAP.write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n');print(f'Regional OSINT v4: {len(clean)} points; precise={sum(precise.values())}; failures after fallback={len(failed)}; counts={counts}')
 if not clean: raise SystemExit('No fresh regional OSINT points from GDELT or Google News RSS')
if __name__=='__main__':main()
