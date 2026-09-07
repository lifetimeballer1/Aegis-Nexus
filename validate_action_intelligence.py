#!/usr/bin/env python3
"""Validate source-backed U.S./China action intelligence end-to-end."""
from __future__ import annotations
import json
from pathlib import Path

DATA=Path('data')
BRAIN=DATA/'intelligence_brain.json'
CANONICAL=DATA/'canonical_intelligence.json'
ACTORS=('United States','China')
SEMANTIC_TYPES={'sanctions','military_action_against','negotiates_with','trades_with','economic_action_toward','technology_action_toward','energy_action_toward','cyber_action_against','political_action_toward'}

def load(path: Path):
    if not path.exists(): raise RuntimeError(f'missing {path}')
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc: raise RuntimeError(f'invalid JSON {path}: {exc}') from exc

def main():
    try:
        brain=load(BRAIN); canonical=load(CANONICAL)
    except RuntimeError as exc:
        print(f'ERROR: {exc}'); return 1
    failures=[]
    layer=brain.get('actionLayer') or {}
    if layer.get('sourceBackedOnly') is not True: failures.append('Brain action layer is not source-backed-only')
    nodes={str(n.get('label')):n for n in brain.get('nodes',[]) if isinstance(n,dict)}
    events=[e for e in canonical.get('events',[]) if isinstance(e,dict)]
    evidence={str(e.get('id')):e for e in canonical.get('evidence',[]) if isinstance(e,dict)}
    relationships=[r for r in canonical.get('relationships',[]) if isinstance(r,dict)]
    entity_ids={str(e.get('id')) for e in canonical.get('entities',[]) if isinstance(e,dict)}
    for actor in ACTORS:
        node=nodes.get(actor)
        if not node:
            failures.append(f'{actor}: major Brain node missing'); continue
        actions=node.get('actions')
        if not isinstance(actions,dict) or not actions: failures.append(f'{actor}: no action categories')
        total=0
        for category,items in (actions or {}).items():
            if not isinstance(items,list): failures.append(f'{actor}: {category} is not a list'); continue
            for i,item in enumerate(items):
                if not isinstance(item,dict): failures.append(f'{actor}/{category}/{i}: invalid evidence object'); continue
                if not str(item.get('title','')).strip(): failures.append(f'{actor}/{category}/{i}: missing title')
                if not (str(item.get('url','')).strip() or str(item.get('source','')).strip()): failures.append(f'{actor}/{category}/{i}: missing source/url')
                total+=1
        declared=int(node.get('actionEvidenceCount') or 0)
        if declared!=total: failures.append(f'{actor}: actionEvidenceCount mismatch ({declared} != {total})')
        if total==0: failures.append(f'{actor}: no evidence-backed actions')
        actor_events=[e for e in events if actor in {str(x) for x in e.get('actor_ids',[]) if x}]
        if not actor_events:
            failures.append(f'{actor}: canonical actor attribution has no action events')
            print(f'{actor}: {total} Brain evidence items; canonical actor events=0'); continue
        attributed=0; targeted=0
        for event in actor_events:
            ev_ids=[str(x) for x in event.get('evidence_ids',[]) if x]
            if ev_ids and all(x in evidence for x in ev_ids): attributed+=1
            if event.get('target_ids'): targeted+=1
            if not str(event.get('action','')).strip(): failures.append(f'{actor}: canonical event {event.get("id")} missing action')
            try: confidence=float(event.get('confidence') or 0)
            except (TypeError,ValueError): confidence=-1
            if not 0 <= confidence <= 1: failures.append(f'{actor}: canonical event {event.get("id")} has invalid confidence')
        if attributed==0: failures.append(f'{actor}: canonical action events have no resolvable evidence')
        if targeted==0: failures.append(f'{actor}: canonical action events have no explicit targets')
        print(f'{actor}: {total} Brain evidence items; canonical actor events={len(actor_events)}, targeted={targeted}')
    semantic_count=0
    for rel in relationships:
        rtype=str(rel.get('relationship_type') or '')
        if rtype not in SEMANTIC_TYPES: continue
        semantic_count+=1
        source=str(rel.get('source_entity_id') or ''); target=str(rel.get('target_entity_id') or '')
        if source not in entity_ids or target not in entity_ids: failures.append(f'semantic relationship {rtype}: invalid entity endpoint')
        if not rel.get('evidence_ids'): failures.append(f'semantic relationship {rtype}: missing evidence_ids')
        if not rel.get('event_ids'): failures.append(f'semantic relationship {rtype}: missing event_ids')
    if semantic_count==0: failures.append('canonical intelligence contains no typed semantic relationships')
    print(f'Canonical semantic relationships: {semantic_count}')
    if failures:
        print('FAIL')
        for failure in failures: print(f'  - {failure}')
        return 1
    print('PASS: U.S./China action attribution, evidence, targets, and semantic relationships are end-to-end backed')
    return 0

if __name__=='__main__': raise SystemExit(main())
