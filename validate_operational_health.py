#!/usr/bin/env python3
"""Phase 8 operational health gate for the canonical Global Pulse refresh."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
ARTIFACTS=('snapshot.json','live_articles.json','map_points.json','intelligence_graph.json','intelligence_brain.json','sources.json')
ARTIFACT_MAX_SKEW_SECONDS=7200
SNAPSHOT_MAX_AGE_SECONDS=7200

def load(name):
    p=DATA/name
    if not p.is_file() or p.stat().st_size==0: raise SystemExit(f'OPERATIONAL HEALTH FAILED: missing {name}')
    try: return json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc: raise SystemExit(f'OPERATIONAL HEALTH FAILED: invalid JSON {name}: {exc}') from exc

def parse_stamp(obj,name):
    value=obj.get('updatedAt') or obj.get('generatedAt') or obj.get('lastSuccessfulRefresh')
    if not value: raise SystemExit(f'OPERATIONAL HEALTH FAILED: {name} has no freshness timestamp')
    try: dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    except ValueError as exc: raise SystemExit(f'OPERATIONAL HEALTH FAILED: {name} has invalid timestamp') from exc
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def main():
    objs={name:load(name) for name in ARTIFACTS}
    stamps={name:parse_stamp(obj,name) for name,obj in objs.items()}
    now=datetime.now(timezone.utc); snapshot_time=stamps['snapshot.json']; snapshot_age=(now-snapshot_time).total_seconds()
    if snapshot_age < -120 or snapshot_age > SNAPSHOT_MAX_AGE_SECONDS: raise SystemExit(f'OPERATIONAL HEALTH FAILED: snapshot.json timestamp age={snapshot_age:.0f}s')
    for name,dt in stamps.items():
        if name!='snapshot.json':
            skew=abs((dt-snapshot_time).total_seconds())
            if skew>ARTIFACT_MAX_SKEW_SECONDS: raise SystemExit(f'OPERATIONAL HEALTH FAILED: {name} freshness skew={skew:.0f}s from canonical snapshot')
    snapshot=objs['snapshot.json']; live=objs['live_articles.json']; points=objs['map_points.json']; graph=objs['intelligence_graph.json']; brain=objs['intelligence_brain.json']
    stories=snapshot.get('stories') or []; articles=live.get('articles') or []; markers=points.get('markers') or []; nodes=graph.get('nodes') or []; edges=graph.get('edges') or []; brain_nodes=brain.get('nodes') or []; brain_edges=brain.get('edges') or []
    if not stories or not articles: raise SystemExit('OPERATIONAL HEALTH FAILED: published news bundle is empty')
    if len(markers)<10: raise SystemExit('OPERATIONAL HEALTH FAILED: published map bundle is too small')
    if len(nodes)<10 or len(edges)<3: raise SystemExit('OPERATIONAL HEALTH FAILED: intelligence graph is too small')
    if len(brain_nodes)<10 or len(brain_edges)<5: raise SystemExit('OPERATIONAL HEALTH FAILED: Intelligence Brain is too small')
    if brain.get('complete') is not True or brain.get('sourceBackedOnly') is not True or brain.get('consolidated') is not True: raise SystemExit('OPERATIONAL HEALTH FAILED: Brain source/consolidation contract missing')
    node_ids={str(n.get('id')) for n in brain_nodes}
    for edge in brain_edges:
        if str(edge.get('source')) not in node_ids or str(edge.get('target')) not in node_ids: raise SystemExit('OPERATIONAL HEALTH FAILED: Brain edge endpoint missing')
        if not edge.get('evidence'): raise SystemExit('OPERATIONAL HEALTH FAILED: Brain relationship lacks evidence')
    # URL is the strongest identity. For records without a URL, include source and
    # title so two legitimate reports with the same headline are not misclassified.
    identity_count=0; unique_identities=set()
    for item in stories:
        url=str(item.get('url') or item.get('sourceUrl') or item.get('link') or '').strip().lower()
        title=str(item.get('title') or item.get('headline') or '').strip().lower()
        source=str(item.get('sourceLabel') or item.get('source') or item.get('sourceName') or item.get('publisher') or '').strip().lower()
        key=url or (f'title:{title}|source:{source}' if title or source else '')
        if not key: raise SystemExit('OPERATIONAL HEALTH FAILED: story lacks provenance identity')
        identity_count+=1; unique_identities.add(key)
    if len(unique_identities)<max(1,int(identity_count*0.9)):
        raise SystemExit('OPERATIONAL HEALTH FAILED: excessive duplicate story identities / excessive duplicate canonical story identities')
    bad_coords=0
    for marker in markers:
        try:
            lat=float(marker.get('lat',marker.get('latitude'))); lng=float(marker.get('lng',marker.get('lon',marker.get('longitude'))))
            if not(-90<=lat<=90 and -180<=lng<=180): bad_coords+=1
        except (TypeError,ValueError): bad_coords+=1
    if bad_coords: raise SystemExit(f'OPERATIONAL HEALTH FAILED: {bad_coords} invalid map coordinates')
    required_snapshot_fields=('updatedAt','lastSuccessfulRefresh','freshness','sourceFailover')
    missing=[x for x in required_snapshot_fields if not snapshot.get(x)]
    if missing: raise SystemExit('OPERATIONAL HEALTH FAILED: snapshot missing '+', '.join(missing))
    print('PASS: Phase 8 operational health gate')
    print(f'stories={len(stories)} liveArticles={len(articles)} mapPoints={len(markers)} graph={len(nodes)}/{len(edges)} brain={len(brain_nodes)}/{len(brain_edges)}')
    print(f'snapshotAge={snapshot_age:.0f}s artifactMaxSkew={ARTIFACT_MAX_SKEW_SECONDS}s uniqueStoryIdentities={len(unique_identities)}')

if __name__=='__main__': main()
