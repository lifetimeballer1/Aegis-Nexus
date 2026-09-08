#!/usr/bin/env python3
"""Deterministic smoke tests for Global Pulse's generated snapshot."""
import json, math, sys
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent / "data" / "snapshot.json"
if not SNAPSHOT.exists():
    print("FAIL: data/snapshot.json missing")
    sys.exit(1)
try:
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"FAIL: invalid snapshot JSON: {exc}")
    sys.exit(1)

errors=[]
def require(cond,msg):
    if not cond: errors.append(msg)

stories=data.get("stories",[])
conflicts=data.get("conflicts",[])
# The browser consumes the canonical coordinate-filtered feed. Snapshot inputs
# may legitimately contain public reports without a geographic location.
try:
    map_data = json.loads((SNAPSHOT.parent / "map_points.json").read_text(encoding="utf-8"))
    markers = map_data["markers"]
except (OSError, ValueError, KeyError, TypeError) as exc:
    print(f"FAIL: invalid canonical map feed: {exc}")
    sys.exit(1)
require(isinstance(stories,list),"stories is not a list")
require(isinstance(conflicts,list),"conflicts is not a list")
require(isinstance(markers,list),"markers/map_markers is not a list")

seen_urls=set()
for i,s in enumerate(stories):
    require(isinstance(s,dict),f"story {i} is not an object")
    if not isinstance(s,dict): continue
    url=str(s.get("url","")).strip()
    if url:
        require(url not in seen_urls,f"duplicate story URL: {url}")
        seen_urls.add(url)

seen_ids=set()
for i,c in enumerate(conflicts):
    require(isinstance(c,dict),f"conflict {i} is not an object")
    if not isinstance(c,dict): continue
    cid=str(c.get("id") or c.get("slug") or c.get("name") or "").strip()
    require(bool(cid),f"conflict {i} missing id/name")
    if cid:
        require(cid not in seen_ids,f"duplicate conflict id: {cid}")
        seen_ids.add(cid)
    for key in ("lat","lon"):
        if key in c and c[key] is not None:
            try:
                value=float(c[key]); require(math.isfinite(value),f"conflict {cid}: invalid {key}")
                if key=="lat": require(-90<=value<=90,f"conflict {cid}: latitude out of range")
                else: require(-180<=value<=180,f"conflict {cid}: longitude out of range")
            except Exception: errors.append(f"conflict {cid}: invalid {key}")

for i,m in enumerate(markers):
    if not isinstance(m,dict): errors.append(f"marker {i} is not an object"); continue
    try:
        lat=float(m.get("lat")); lon=float(m.get("lon",m.get("lng")))
        require(-90<=lat<=90,f"marker {i}: latitude out of range")
        require(-180<=lon<=180,f"marker {i}: longitude out of range")
    except Exception:
        errors.append(f"marker {i}: missing/invalid coordinates")

# Coverage regression: the new monitoring layer must remain represented when it has evidence.
coverage=data.get("conflict_coverage",data.get("coverage",[]))
if coverage:
    require(isinstance(coverage,list),"coverage layer is not a list")
    for item in coverage:
        if not isinstance(item,dict): errors.append("coverage item is not an object"); continue
        require(item.get("name") or item.get("id"),"coverage item missing name/id")
        if "confidence" in item:
            require(str(item["confidence"]).upper() in {"CORROBORATED","MULTI-SOURCE","SINGLE-SOURCE","MONITORING","NO CURRENT SIGNAL"},f"invalid coverage confidence: {item['confidence']}")

if errors:
    print("PIPELINE VALIDATION FAILED")
    for e in errors: print(" -",e)
    sys.exit(1)
print(f"PIPELINE VALIDATION PASSED: {len(stories)} stories, {len(conflicts)} conflicts, {len(markers)} map markers")
