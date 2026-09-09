#!/usr/bin/env python3
"""Expand live map coverage for Africa, South America and South Asia.

Uses public GDELT GEO PointData plus current Global Pulse reporting. GDELT points
are discovery signals, not automatically confirmed incidents. Reported-area points
are explicitly labelled and retain source URLs. No API key is required.
"""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / "data" / "snapshot.json"
UA = "GlobalPulse/1.2 (+https://github.com/lifetimeballer1/global-pulse)"

REGIONS = {
    "South America": {
        "countries": ["brazil","colombia","venezuela","ecuador","peru","bolivia","paraguay","uruguay","argentina","chile","guyana","suriname"],
        "queries": ["(conflict OR attack OR fighting OR bombing OR shooting OR cartel OR gang OR guerrilla OR insurgent)", "(violence OR clash OR killed OR kidnapping OR military OR protest)"],
    },
    "Africa": {
        "countries": ["sudan","southsudan","democraticrepublicofthecongo","nigeria","somalia","ethiopia","kenya","mozambique","cameroon","centralafricanrepublic","libya","mali","burkinafaso","niger","chad","tanzania","uganda","southafrica","angola","senegal","ghana","guinea","sierra leone","ivorycoast"],
        "queries": ["(conflict OR attack OR fighting OR bombing OR shooting OR insurgent OR militia OR jihadist)", "(violence OR clash OR killed OR kidnapping OR military OR coup OR protest)"],
    },
    "South Asia": {
        "countries": ["india","pakistan","bangladesh","afghanistan","srilanka","nepal","bhutan","maldives","myanmar"],
        "queries": ["(conflict OR attack OR fighting OR bombing OR shooting OR insurgent OR militant OR terrorism)", "(violence OR clash OR killed OR kidnapping OR military OR border OR protest)"],
    },
}

PLACE_POINTS = {
    # South America
    "Manaus": (-3.1190,-60.0217), "Belem": (-1.4558,-48.4902), "Fortaleza": (-3.7319,-38.5267), "Recife": (-8.0476,-34.8770),
    "Salvador": (-12.9777,-38.5016), "Rio de Janeiro": (-22.9068,-43.1729), "Sao Paulo": (-23.5505,-46.6333), "Brasilia": (-15.7939,-47.8828),
    "Medellin": (6.2442,-75.5812), "Cali": (3.4516,-76.5320), "Bogota": (4.7110,-74.0721), "Barranquilla": (10.9685,-74.7813),
    "Buenaventura": (3.8801,-77.0312), "Cucuta": (7.8891,-72.4967), "Arauca": (7.0903,-70.7617),
    "Caracas": (10.4806,-66.9036), "Maracaibo": (10.6545,-71.6299), "Ciudad Guayana": (8.3512,-62.6410),
    "Guayaquil": (-2.1709,-79.9224), "Quito": (-0.1807,-78.4678), "Esmeraldas": (0.9682,-79.6517), "Manta": (-0.9677,-80.7089),
    "Lima": (-12.0464,-77.0428), "Arequipa": (-16.4090,-71.5375), "Cusco": (-13.5319,-71.9675),
    "La Paz": (-16.4897,-68.1193), "Santa Cruz": (-17.8146,-63.1561), "Asuncion": (-25.2637,-57.5759),
    "Santiago": (-33.4489,-70.6693), "Buenos Aires": (-34.6037,-58.3816),
    # Africa
    "Khartoum": (15.5007,32.5599), "Omdurman": (15.6445,32.4777), "El Fasher": (13.6279,25.3494), "Nyala": (12.0539,24.8803), "Port Sudan": (19.6158,37.2164),
    "Juba": (4.8594,31.5713), "Wau": (7.7029,28.0030), "Malakal": (9.5334,31.6605),
    "Kinshasa": (-4.4419,15.2663), "Goma": (-1.6771,29.2285), "Beni": (0.4917,29.4733), "Bukavu": (-2.5083,28.8608), "Lubumbashi": (-11.6876,27.5026),
    "Mogadishu": (2.0469,45.3182), "Kismayo": (-0.3582,42.5454), "Baidoa": (3.1167,43.6500), "Hargeisa": (9.5624,44.0770),
    "Addis Ababa": (9.0320,38.7469), "Mekelle": (13.4967,39.4767), "Gondar": (12.6030,37.4521), "Bahir Dar": (11.5742,37.3614),
    "Lagos": (6.5244,3.3792), "Maiduguri": (11.8333,13.1500), "Kano": (12.0022,8.5920), "Kaduna": (10.5105,7.4165), "Abuja": (9.0765,7.3986), "Zamfara": (12.1844,6.2376),
    "Bamenda": (5.9631,10.1591), "Buea": (4.1550,9.2310), "Kumba": (4.6363,9.4469), "Yaounde": (3.8480,11.5021),
    "Mocimboa da Praia": (-11.3467,40.3500), "Palma": (-10.7736,40.5260), "Pemba": (-12.9739,40.5178), "Nampula": (-15.1165,39.2666),
    "Tripoli": (32.8872,13.1913), "Benghazi": (32.1194,20.0868), "Misrata": (32.3754,15.0925), "Sabha": (27.0377,14.4283),
    "Mali": (17.5707,-4.0026), "Bamako": (12.6392,-8.0029), "Gao": (16.2717,-0.0447), "Timbuktu": (16.7666,-3.0026),
    "Ouagadougou": (12.3714,-1.5197), "Niamey": (13.5127,2.1126), "N'Djamena": (12.1348,15.0557),
    "Bangui": (4.3947,18.5582), "Bambari": (5.7623,20.6672), "Mbuji-Mayi": (-6.1360,23.5898),
    "Nairobi": (-1.2864,36.8172), "Mombasa": (-4.0435,39.6682), "Kampala": (0.3476,32.5825), "Dar es Salaam": (-6.7924,39.2083),
    "Johannesburg": (-26.2041,28.0473), "Cape Town": (-33.9249,18.4241), "Luanda": (-8.8390,13.2894),
    # South Asia
    "Kabul": (34.5553,69.2075), "Kandahar": (31.6289,65.7372), "Herat": (34.3529,62.2040), "Jalalabad": (34.4348,70.4500), "Kunduz": (36.7280,68.8681),
    "Islamabad": (33.6844,73.0479), "Peshawar": (34.0151,71.5249), "Quetta": (30.1798,66.9750), "Karachi": (24.8607,67.0011), "Lahore": (31.5204,74.3587),
    "Balochistan": (28.4907,65.0958), "Khyber Pakhtunkhwa": (34.9526,72.3311),
    "New Delhi": (28.6139,77.2090), "Srinagar": (34.0837,74.7973), "Jammu": (32.7266,74.8570), "Manipur": (24.6637,93.9063), "Imphal": (24.8170,93.9368), "Kashmir": (34.0837,74.7973),
    "Mumbai": (19.0760,72.8777), "Kolkata": (22.5726,88.3639), "Hyderabad": (17.3850,78.4867), "Chennai": (13.0827,80.2707),
    "Dhaka": (23.8103,90.4125), "Chittagong": (22.3569,91.7832), "Cox's Bazar": (21.4272,92.0058),
    "Colombo": (6.9271,79.8612), "Jaffna": (9.6615,80.0255), "Kathmandu": (27.7172,85.3240), "Naypyidaw": (19.7633,96.0785), "Yangon": (16.8409,96.1735), "Mandalay": (21.9588,96.0891), "Rakhine": (20.0,93.0),
}

STRONG = re.compile(r"\b(airstrike|air strike|bombing|missile|rocket|killed|dead|attack|clash|fighting|offensive|ambush|massacre|kidnap|kidnapping|gang|cartel|militia|insurgent|terrorist|raid|shooting|violence|battle|siege|explosion|drone|war|shelling|artillery|protest|unrest|coup)\b", re.I)
NEGATE = re.compile(r"\b(historical|history of|anniversary|documentary|book review|explainer|what is|how to|vacation|travel|recipe|sport|movie|music)\b", re.I)

def fetch_json(url):
    req=Request(url,headers={"User-Agent":UA,"Accept":"application/json,*/*"})
    with urlopen(req,timeout=25) as r: return json.loads(r.read().decode("utf-8",errors="replace"))

def text_of(a): return " ".join(str(a.get(k) or "") for k in ("title","summary","summary_snippet","description","text","detail"))

def domain(a):
    try: return (urlparse(str(a.get("url") or "")).hostname or "").lower().removeprefix("www.")
    except Exception: return ""

def gdelt_region_points(region,country,query):
    q=f'locationcc:{country} {query}'
    url="https://api.gdeltproject.org/api/v2/geo/geo?query="+quote(q)+"&mode=PointData&format=GeoJSON&timespan=1d&maxrecords=120"
    try:
        obj=fetch_json(url); out=[]
        for f in obj.get("features",[]):
            c=(f.get("geometry") or {}).get("coordinates") or []
            if len(c)<2: continue
            try: lng,lat=float(c[0]),float(c[1])
            except (TypeError,ValueError): continue
            if not (-90<=lat<=90 and -180<=lng<=180): continue
            p=f.get("properties") or {}; url2=str(p.get("url") or "")
            out.append({"lat":lat,"lng":lng,"title":str(p.get("name") or "GDELT geolocated signal")[:180],"detail":str(p.get("html") or p.get("description") or "Current GDELT GEO signal")[:300],"url":url2,"sourceUrl":url2,"source":"GDELT GEO","sourceDomain":"gdeltproject.org","eventType":"OSINT/GEO","layer":"osint-regional","region":region,"country":country,"confidence":"DISCOVERY SIGNAL","observedAt":datetime.now(timezone.utc).isoformat()})
        return out
    except Exception as e:
        print(f"GDELT {region}/{country} unavailable: {e}"); return []

def reported_points(stories):
    out=[]; seen=set(); stories=sorted(stories,key=lambda a:str(a.get("published_date") or a.get("published") or a.get("time") or ""),reverse=True)
    for a in stories:
        txt=text_of(a)
        if NEGATE.search(txt) or not STRONG.search(txt): continue
        low=txt.lower(); url=str(a.get("url") or "")
        for place,(lat,lng) in PLACE_POINTS.items():
            if place.lower() not in low: continue
            key=(place.lower(),url or str(a.get("title") or ""))
            if key in seen: continue
            seen.add(key)
            out.append({"lat":lat,"lng":lng,"title":f"Reported activity — {place}","detail":str(a.get("title") or "Current public report")[:240],"url":url,"sourceUrl":url,"source":str(a.get("source") or "Global Pulse news pipeline"),"eventType":"REPORTED AREA","layer":"osint-regional","confidence":"OSINT REPORT","observedAt":a.get("published_date") or a.get("published") or a.get("time")})
            if len(out)>=450: return out
    return out

def main():
    snap=json.loads(SNAP.read_text(encoding="utf-8"))
    base=[m for m in (snap.get("markers") or []) if m.get("layer")!="osint-regional"]
    stories=list(snap.get("stories") or [])+list((snap.get("liveArticles") or {}).get("articles") or [])
    points=[]
    for region, cfg in REGIONS.items():
        for country in cfg["countries"]:
            # One focused query per country; two queries would multiply volume without adding much signal.
            points.extend(gdelt_region_points(region,country,cfg["queries"][0]))
    # Keep highest geographic diversity: cap repeated exact coordinates.
    seen=set(); clean=[]
    for p in points:
        key=(round(p["lat"],3),round(p["lng"],3),p.get("url") or "")
        if key in seen: continue
        seen.add(key); clean.append(p)
    reports=reported_points(stories)
    snap["markers"]=base+clean[:700]+reports
    snap["regionalOsint"]={
        "version":1,"updatedAt":datetime.now(timezone.utc).isoformat(),
        "regions":{r:{"gdeltPoints":sum(1 for p in clean if p.get("region")==r),"reportedAreaPoints":sum(1 for p in reports if p.get("region")==r)} for r in REGIONS},
        "sources":[{"name":"GDELT GEO","cadence":"each Global Pulse refresh","points":len(clean),"url":"https://www.gdeltproject.org/"},{"name":"Global Pulse reported-area extraction","cadence":"each Global Pulse refresh","points":len(reports),"url":"https://github.com/lifetimeballer1/global-pulse"}]
    }
    changes=snap.get("changes") or []; changes.insert(0,{"kind":"system","title":"Regional OSINT expansion refreshed","detail":f"Added {len(clean[:700])} GDELT regional signals and {len(reports)} current reported-area points across Africa, South America and South Asia."}); snap["changes"]=changes[:8]
    SNAP.write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n")
    print(f"Regional OSINT: {len(clean[:700])} GDELT points + {len(reports)} reported-area points")

if __name__=="__main__": main()
