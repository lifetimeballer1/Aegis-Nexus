#!/usr/bin/env python3
"""Final production pass for source health and Global Tension calibration.

Runs after all snapshot/layer builders. It makes the dashboard's source-health
panel describe the actual collector result and makes tension responsive to
high-impact active conflict events instead of headline volume alone.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; SNAP=DATA/'snapshot.json'; STATUS=DATA/'live_status.json'; SOURCES=DATA/'sources.json'; HISTORY=DATA/'history.json'
DRIVER_WEIGHTS={'Conflict activity':.22,'Diplomatic strain':.15,'Economic pressure':.16,'Market volatility':.10,'Military posture':.25,'Climate & humanitarian pressure':.12}
SEV={'critical':100,'high':88,'elevated':72,'moderate':58,'low':38,'watch':45}

def num(v,default=0):
 try:return float(v)
 except:return default

def age_hours(v):
 try:return max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(str(v).replace('Z','+00:00'))).total_seconds()/3600)
 except:return 999

def host(url):
 try:return urlparse(str(url)).netloc.lower().removeprefix('www.')
 except:return ''

def build_source_health(d):
 stories=d.get('stories',[]) if isinstance(d.get('stories'),list) else []
 old=d.get('sourceHealth',[]) if isinstance(d.get('sourceHealth'),list) else []
 live={}
 try: live=json.loads(STATUS.read_text(encoding='utf-8'))
 except: live={}
 live_by={str(x.get('name') or x.get('source') or ''):x for x in live.get('sources',[]) if isinstance(x,dict)}
 rows=[]
 for x in old:
  name=str(x.get('name','')); matches=[s for s in stories if str(s.get('sourceLabel',''))==name]; urls=[host(s.get('url') or s.get('source')) for s in matches]; urls={u for u in urls if u}
  lv=live_by.get(name,{})
  raw=str(x.get('status','unknown')).lower(); status='ONLINE' if raw in ('ok','online','healthy') else 'FAILED' if raw in ('error','failed','offline') else 'UNKNOWN'
  if not matches and raw=='ok': status='DEGRADED'
  rows.append({'name':name,'type':x.get('type','general'),'status':status.lower(),'label':status,'articles':len(matches),'domains':len(urls),'lastChecked':d.get('updatedAt'),'error':x.get('error') or lv.get('error','')})
 rows.sort(key=lambda x:(x['status']!='online',x['status']!='degraded',x['name']))
 d['sourceHealth']=rows
 d['sourceHealthSummary']={'total':len(rows),'online':sum(x['status']=='online' for x in rows),'degraded':sum(x['status']=='degraded' for x in rows),'failed':sum(x['status']=='failed' for x in rows),'lastChecked':d.get('updatedAt'),'method':'Feed collector status plus articles returned in the current snapshot.'}
 return rows

def conflict_pressure(d, stories):
 conflicts=d.get('conflicts',[]) if isinstance(d.get('conflicts'),list) else []
 vals=[]
 for c in conflicts:
  score=num(c.get('activityScore',c.get('score',c.get('tension',c.get('priority',0)))))
  sev=str(c.get('severity',c.get('status',''))).lower(); score=max(score,SEV.get(sev,0)) if sev in ('critical','high') else score
  if score>0: vals.append(score)
 vals.sort(reverse=True)
 if not vals:return 35
 top=vals[:8]; return max(35,min(92,round(sum(v*(1/(i+1)**.45) for i,v in enumerate(top))/sum(1/(i+1)**.45 for i in range(len(top))))))

def event_intensity(stories, patterns):
 rx=re.compile(patterns,re.I); total=0; domains=set(); recent=0; high=0
 for s in stories:
  text=' '.join(str(s.get(k,'')) for k in ('title','summary','tag','sourceLabel','sourceType'))
  if not rx.search(text):continue
  w=1; age=age_hours(s.get('time') or s.get('published_date'))
  if age<=6:w=1.5;recent+=1
  elif age<=24:w=1.25;recent+=1
  elif age>72:w=.65
  if re.search(r'\b(missile|airstrike|drone|invasion|offensive|troops?|strike|killed|attack|bomb|mobiliz|blockade|intercepted)\b',text,re.I):w*=1.25;high+=1
  total+=w; domains.add(host(s.get('url') or s.get('source')))
 density=min(1,total/28); diversity=min(1,len(domains)/8); freshness=min(1,recent/10)
 return round(35+38*density+15*diversity+12*freshness+min(10,high)*.5)

def recalibrate(d):
 stories=d.get('stories',[]) if isinstance(d.get('stories'),list) else []
 b=d.get('breakdownScores',{}) if isinstance(d.get('breakdownScores'),dict) else {}
 conflict=event_intensity(stories,r'\b(war|armed conflict|fighting|battle|offensive|airstrike|shelling|invasion|insurgent|militant attack|clash|bombing|missile|drone|strike)\b')
 military=event_intensity(stories,r'\b(military|troops?|forces?|missile|missiles|drone|drones|airstrike|air strikes|bombers?|carrier|navy|mobiliz|exercise|weapons?|deployment|offensive|strike)\b')
 diplomatic=event_intensity(stories,r'\b(sanction|sanctions|ultimatum|diplomatic crisis|expulsion|negotiation|ceasefire talks|treaty|envoy|foreign minister|alliance)\b')
 economic=event_intensity(stories,r'\b(inflation|tariff|tariffs|trade war|recession|supply disruption|oil price|gas price|shipping|freight|central bank|interest rate|gdp|economy|sanction)\b')
 market=event_intensity(stories,r'\b(stock market|stocks|shares|bond yields?|treasury yields?|currency|forex|exchange rate|dollar|euro|yen|yuan|oil prices?|crude prices?|natural gas prices?|market volatility|market selloff|market rally|plunge|surge)\b')
 climate=event_intensity(stories,r'\b(drought|water shortage|water stress|water scarcity|flood|flooding|cyclone|hurricane|typhoon|storm surge|landslide|heatwave|extreme heat|wildfire|food insecurity|famine|acute hunger|epidemic|outbreak|cholera|malaria|pandemic)\b')
 cp=conflict_pressure(d,stories)
 floors={'Conflict activity':max(conflict,cp),'Diplomatic strain':diplomatic,'Economic pressure':economic,'Market volatility':market,'Military posture':max(military,cp*.9),'Climate & humanitarian pressure':climate}
 for k,v in floors.items(): b[k]=int(round(max(num(b.get(k),35),min(100,v))))
 d['breakdownScores']=b
 d['tension']=int(round(sum(b[k]*DRIVER_WEIGHTS[k] for k in DRIVER_WEIGHTS)))
 d['tensionDelta']=0
 d['scoreVersion']=5
 d['tensionMethod']='V5: evidence-weighted six-driver index with bounded event-intensity and active-conflict pressure floors. Duplicate headlines are not counted as independent events.'
 d['earlyWarning']={'level':'HIGH' if d['tension']>=75 else 'ELEVATED' if d['tension']>=55 else 'WATCH','score':d['tension'],'direction':'stable','momentum':0.0,'strongestDriver':max(b,key=b.get),'strongestDriverScore':b[max(b,key=b.get)],'method':'Current V5 tension snapshot.'}
 return d

def sync_history(d):
 """Keep the trend chart on the same score version as the live snapshot."""
 try:
  history=json.loads(HISTORY.read_text(encoding='utf-8'))
  if not isinstance(history,list): history=[]
 except Exception:
  history=[]
 version=int(num(d.get('scoreVersion'),5)); current_time=str(d.get('updatedAt') or datetime.now(timezone.utc).isoformat()); current_score=num(d.get('tension'))
 versioned=[x for x in history if isinstance(x,dict) and int(num(x.get('scoreVersion'),0))==version]
 prev=versioned[-1] if versioned else None
 delta=round(current_score-num(prev.get('tension')) if prev else 0,1)
 history=[x for x in history if not (isinstance(x,dict) and int(num(x.get('scoreVersion'),0)) not in (0,version))]
 if not history and prev: history=[prev]
 history.append({'updatedAt':current_time,'tension':int(round(current_score)),'delta':delta,'scoreVersion':version})
 history=history[-48:]
 HISTORY.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 d['tensionDelta']=delta
 level='HIGH' if d['tension']>=75 else 'ELEVATED' if d['tension']>=55 else 'WATCH'; direction='rising' if delta>2 else 'falling' if delta<-2 else 'stable'; b=d.get('breakdownScores',{}); strongest=max(b,key=b.get) if b else ''
 d['earlyWarning']={'level':level,'score':d['tension'],'direction':direction,'momentum':delta,'strongestDriver':strongest,'strongestDriverScore':b.get(strongest,0),'method':'Current V5 tension snapshot compared with the previous V5 snapshot.'}
 return history

def main():
 d=json.loads(SNAP.read_text(encoding='utf-8')); build_source_health(d); recalibrate(d); sync_history(d); SNAP.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 try:
  s=json.loads(SOURCES.read_text(encoding='utf-8'));s['sourceHealth']=d['sourceHealthSummary'];SOURCES.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 except Exception:pass
 print('FINAL INTELLIGENCE:',d['tension'],d['breakdownScores']); print('SOURCE HEALTH:',d['sourceHealthSummary']); print('HISTORY:',d.get('tensionDelta'),d['earlyWarning'])

if __name__=='__main__':main()
