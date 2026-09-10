#!/usr/bin/env python3
"""Fetch public World Bank macro indicators; no API key required."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';SNAP=DATA/'snapshot.json';BASE='https://api.worldbank.org/v2/country/all/indicator/'
INDICATORS={'GDP growth':'NY.GDP.MKTP.KD.ZG','Inflation':'FP.CPI.TOTL.ZG','Trade (% GDP)':'NE.TRD.GNFS.ZS','Unemployment':'SL.UEM.TOTL.ZS'}
UA='GlobalPulse/20.0 (+https://github.com/lifetimeballer1/global-pulse)'
def fetch(indicator):
    q=urlencode({'format':'json','mrv':'3','per_page':'1000'});req=Request(BASE+indicator+'?'+q,headers={'User-Agent':UA})
    with urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8'))
def main():
    snap=json.loads(SNAP.read_text(encoding='utf-8')) if SNAP.exists() else {};out=[];errors=[]
    for name,code in INDICATORS.items():
        try:
            payload=fetch(code);rows=payload[1] if isinstance(payload,list) and len(payload)>1 else []
            for row in rows:
                if row.get('value') is None:continue
                out.append({'indicator':name,'code':code,'country':row.get('country',{}).get('value'),'countryCode':row.get('countryiso3code'),'period':row.get('date'),'value':row.get('value'),'source':'World Bank WDI','sourceUrl':'https://data.worldbank.org/','retrievedAt':datetime.now(timezone.utc).isoformat()})
        except Exception as exc:errors.append(f'{name}: {type(exc).__name__}: {exc}')
    snap['macroData']={'provider':'World Bank World Development Indicators','updatedAt':datetime.now(timezone.utc).isoformat(),'noApiKey':True,'indicators':out,'errors':errors,'note':'Annual macro context; reporting and market layers are not treated as causal evidence.'};snap['updatedAt']=datetime.now(timezone.utc).isoformat();SNAP.write_text(json.dumps(snap,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print(f'World Bank macro: {len(out)} observations, errors={len(errors)}')
if __name__=='__main__':main()
