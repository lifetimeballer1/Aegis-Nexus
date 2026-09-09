#!/usr/bin/env python3
"""Publish a compact, canonical geographic marker feed for the browser."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
SNAP=DATA/'snapshot.json'
BRAIN=DATA/'intelligence_brain.json'
OUT=DATA/'map_points.json'

# Representative country coordinates are deliberately labeled as country references,
# not incident locations. They let the situation map visualize source-backed Brain
# country nodes without manufacturing precision about where an event occurred.
COUNTRY_REF={
    'united-states':(38.0,-97.0),'iran':(32.0,53.0),'israel':(31.5,34.8),'yemen':(15.5,48.0),
    'saudi-arabia':(24.0,45.0),'iraq':(33.2,43.7),'syria':(35.0,38.0),'lebanon':(33.9,35.8),
    'jordan':(31.2,36.2),'turkey':(39.0,35.0),'russia':(61.5,105.3),'ukraine':(49.0,32.0),
    'china':(35.9,104.2),'taiwan':(23.7,121.0),'north-korea':(40.3,127.5),'south-korea':(36.5,127.9),
    'japan':(36.2,138.3),'india':(22.9,79.0),'pakistan':(30.4,69.3),'afghanistan':(33.9,67.7),
    'mexico':(23.6,-102.6),'canada':(56.1,-106.3),'colombia':(4.6,-74.1),'ecuador':(-1.8,-78.2),
    'venezuela':(6.4,-66.6),'brazil':(-10.8,-51.9),'united-kingdom':(55.4,-3.4),'uk':(55.4,-3.4),
    'france':(46.2,2.2),'germany':(51.2,10.5),'italy':(42.8,12.8),'poland':(52.1,19.1),
    'romania':(45.9,24.9),'greece':(39.1,21.8),'egypt':(26.8,30.8),'sudan':(12.9,30.2),
    'libya':(26.3,17.2),'nigeria':(9.1,8.7),'somalia':(5.2,46.2),'ethiopia':(9.1,40.5),
    'south-africa':(-30.6,22.9),'australia':(-25.3,133.8)
}
STRATEGIC_REF={
    'hormuz':(26.6,56.3),'strait-of-hormuz':(26.6,56.3),'bab-el-mandeb':(12.6,43.3),
    'suez':(30.5,32.3),'suez-canal':(30.5,32.3),'panama':(9.1,-79.7),'panama-canal':(9.1,-79.7),
    'malacca':(2.5,101.8),'strait-of-malacca':(2.5,101.8)
}

def num(v):
    try:
        n=float(v); return n if n==n else None
    except (TypeError,ValueError): return None

def coord(item):
    if not isinstance(item,dict): return None
    lat=num(item.get('lat',item.get('latitude',item.get('lat_deg'))))
    lng=num(item.get('lng',item.get('lon',item.get('longitude',item.get('long')))))
    c=item.get('coordinates')
    if (lat is None or lng is None) and isinstance(c,dict):
        lat=num(c.get('lat',c.get('latitude',lat))); lng=num(c.get('lng',c.get('lon',c.get('longitude',lng))))
    elif (lat is None or lng is None) and isinstance(c,list) and len(c)>=2:
        lng=num(c[0]); lat=num(c[1])
    g=item.get('geometry')
    if (lat is None or lng is None) and isinstance(g,dict) and isinstance(g.get('coordinates'),list) and len(g['coordinates'])>=2:
        lng=num(g['coordinates'][0]); lat=num(g['coordinates'][1])
    if lat is None or lng is None or abs(lat)>90 or abs(lng)>180: return None
    return round(lat,5),round(lng,5)

def flatten(value,out=None,seen=None,depth=0):
    out=[] if out is None else out; seen=set() if seen is None else seen
    if depth>8 or not isinstance(value,(dict,list)): return out
    if isinstance(value,list):
        for x in value: flatten(x,out,seen,depth+1)
        return out
    ident=id(value)
    if ident in seen: return out
    seen.add(ident)
    c=coord(value)
    if c:
        x=dict(value); x['lat'],x['lng']=c; out.append(x)
    for child in value.values():
        if isinstance(child,(dict,list)): flatten(child,out,seen,depth+1)
    return out

def marker_key(m):
    return str(m.get('id') or m.get('eventId') or m.get('mapId') or m.get('datasetEventId') or m.get('sourceUrl') or m.get('url') or f"{m.get('lat')}|{m.get('lng')}|{m.get('title') or m.get('name') or m.get('location') or ''}")

def brain_reference_points():
    if not BRAIN.exists(): return []
    try: brain=json.loads(BRAIN.read_text(encoding='utf-8'))
    except Exception: return []
    points=[]
    for node in brain.get('nodes',[]):
        if not isinstance(node,dict): continue
        nid=str(node.get('id') or '').lower()
        label=str(node.get('label') or node.get('name') or node.get('id') or '').strip()
        c=COUNTRY_REF.get(nid) or STRATEGIC_REF.get(nid)
        if not c:
            compact=nid.replace('_','-').replace(' ','-')
            c=COUNTRY_REF.get(compact) or STRATEGIC_REF.get(compact)
        if not c: continue
        ev=(node.get('evidence') or [{}])[0] or {}
        points.append({
            'id':f"brain-ref-{nid}",'nodeId':nid,'label':label,'name':label,
            'title':f"{label} — intelligence reference",'lat':c[0],'lng':c[1],
            'kind':node.get('kind'),'layer':'osint','brainNode':True,
            'geoPrecision':'country-reference' if nid in COUNTRY_REF else 'strategic-reference',
            'detail':f"Regional reference for the source-backed Intelligence Brain node {label}. This point is not an incident location.",
            'source':ev.get('source'),'url':ev.get('url')
        })
    return points

def main():
    snap=json.loads(SNAP.read_text(encoding='utf-8'))
    sources=[snap.get('markers'),(snap.get('osintMaps') or {}).get('regionalPoints'),(snap.get('osintMaps') or {}).get('markers'),(snap.get('conflictDataset') or {}).get('markers'),snap.get('mapPoints'),snap.get('map_points')]
    points=[]
    for src in sources:
        if isinstance(src,list): points.extend(flatten(src))
    if len(points)<10: points=flatten(snap)
    # Preserve any exact geographic observations first; use explicit Brain references
    # only to guarantee a useful global map when upstream reports lack coordinates.
    points.extend(brain_reference_points())
    out=[];seen=set()
    for p in points:
        k=marker_key(p)
        if k in seen: continue
        seen.add(k); p.pop('geometry',None); p.pop('coordinates',None); out.append(p)
    if not out: raise RuntimeError('map_points.json contains zero valid geographic markers')
    payload={'version':3,'updatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'count':len(out),'source':'canonical snapshot geographic intelligence layers plus source-backed Brain regional references','markers':out}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
    print(f'MAP POINTS: {len(out)} valid geographic markers')

if __name__=='__main__': raise SystemExit(main())
