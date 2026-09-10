#!/usr/bin/env python3
"""Publish the Intelligence Web artifact from the authoritative snapshot.

The graph is a presentation projection of canonical intelligence. Preserve
source metadata so the Web can render intelligence context without creating a
second source of truth or inventing relationships.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / 'data' / 'snapshot.json'
OUT = ROOT / 'data' / 'intelligence_graph.json'

NODE_FIELDS = (
    'id', 'label', 'name', 'canonical_name', 'kind', 'type', 'mentions',
    'importance', 'confidence', 'strategic_relevance', 'geographic_relevance',
    'country', 'region', 'lat', 'lon', 'latitude', 'longitude', 'entity_type',
    'actor_role', 'target_role', 'roles', 'events', 'event_ids', 'updatedAt',
    'time', 'status', 'eventIds',
)
EDGE_FIELDS = (
    'source', 'target', 'sid', 'tid', 'weight', 'types', 'relationship',
    'confidence', 'importance', 'strategic_relevance', 'geographic_relevance',
    'actor_role', 'target_role', 'roles', 'event_ids', 'events', 'updatedAt',
    'time', 'status', 'eventIds', 'strength',
)


def _recency_score(node):
    dates = [e.get('time') for e in (node.get('evidence') or [])
             if isinstance(e, dict) and e.get('time')]
    raw = node.get('updatedAt') or node.get('time') or (max(dates) if dates else '')
    if not raw:
        return 0
    try:
        dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
        age = max(0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
        return 30 if age <= 1 else 20 if age <= 3 else 10 if age <= 7 else 0
    except Exception:
        return 0


def node_rank(node):
    evidence = node.get('evidence') or []
    text = ' '.join(str(x.get(k, '')).lower() for x in evidence
                    if isinstance(x, dict) for k in ('title', 'source'))
    breaking = 12 if any(k in text for k in (
        'breaking', 'urgent', 'attack', 'strike', 'invasion', 'ceasefire', 'sanction'
    )) else 0
    return int(node.get('mentions') or 0) * 2 + math.log1p(len(evidence)) * 8 + _recency_score(node) + breaking


def _copy_known_fields(source, fields):
    return {key: source[key] for key in fields if key in source and source[key] is not None}


def _merge_metadata(source, target):
    for key, value in source.items():
        if key in ('id', 'source', 'target', 'sid', 'tid'):
            continue
        if key not in target and value is not None:
            target[key] = value


def main():
    data = json.loads(SNAP.read_text(encoding='utf-8'))
    graph = data.get('intelligenceGraph') or {}

    raw_nodes = [n for n in graph.get('nodes', []) if isinstance(n, dict) and n.get('id')]
    nodes = []
    for raw in raw_nodes:
        node = _copy_known_fields(raw, NODE_FIELDS)
        node['id'] = str(raw.get('id'))
        node['label'] = str(raw.get('label') or raw.get('name') or raw.get('canonical_name') or raw.get('id'))
        node['kind'] = str(raw.get('kind') or raw.get('type') or raw.get('entity_type') or 'actor')
        node['mentions'] = int(raw.get('mentions') or 0)
        node['evidence'] = [e for e in (raw.get('evidence') or [])[:12] if isinstance(e, dict)]
        nodes.append(node)

    valid = {n['id'] for n in nodes}
    label_to_id = {}
    for node in nodes:
        for label in (node.get('label'), node.get('name'), node.get('canonical_name')):
            if label:
                label_to_id[str(label).strip().lower()] = node['id']
    id_to_id = {str(n['id']): str(n['id']) for n in nodes}

    def resolve(value):
        value = str(value or '').strip()
        return id_to_id.get(value) or label_to_id.get(value.lower()) or label_to_id.get(value.replace('_', ' ').lower())

    edges = []
    seen = {}
    for raw in graph.get('edges', []):
        if not isinstance(raw, dict):
            continue
        source = resolve(raw.get('source') or raw.get('sid'))
        target = resolve(raw.get('target') or raw.get('tid'))
        evidence = [x for x in (raw.get('evidence') or [])[:12]
                    if isinstance(x, dict) and (x.get('title') or x.get('url') or x.get('link'))]
        if source not in valid or target not in valid or source == target or not evidence:
            continue

        edge = _copy_known_fields(raw, EDGE_FIELDS)
        edge.update({
            'source': source,
            'target': target,
            'weight': max(1, int(raw.get('weight') or 1)),
            'types': list(raw.get('types') or []),
            'relationship': str(raw.get('relationship') or 'Both entities are referenced in the same public evidence record.'),
            'evidence': evidence,
            'evidenceCount': len(evidence),
        })

        # Different actions between the same endpoints are separate claims.
        key = (source, edge['relationship'], target)
        if key not in seen:
            seen[key] = edge
            edges.append(edge)
        else:
            existing = seen[key]
            existing['weight'] = max(existing['weight'], edge['weight'])
            existing['evidence'] = (existing.get('evidence') or []) + edge['evidence']
            existing['evidence'] = existing['evidence'][:12]
            existing['evidenceCount'] = len(existing['evidence'])
            existing['types'] = list(dict.fromkeys((existing.get('types') or []) + edge['types']))
            for field in ('eventIds', 'event_ids'):
                if field in edge:
                    existing[field] = list(dict.fromkeys(existing.get(field, []) + edge[field]))
            _merge_metadata(edge, existing)

    degree = {node['id']: 0 for node in nodes}
    for edge in edges:
        degree[edge['source']] += 1
        degree[edge['target']] += 1

    for node in nodes:
        node['importance'] = round(max(float(node.get('importance') or 0), node_rank(node)) + degree[node['id']] * 5, 3)

    nodes.sort(key=lambda n: (n['importance'], n['mentions'], n['label']), reverse=True)
    edges.sort(key=lambda e: (e['weight'], e['evidenceCount']), reverse=True)
    published_ids = {node['id'] for node in nodes[:100]}
    edges = [edge for edge in edges if edge['source'] in published_ids and edge['target'] in published_ids]

    payload = {
        'updatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'method': graph.get('method') or 'Evidence-backed public reporting graph',
        'caution': graph.get('caution') or 'A connection means the entities share a public evidence record; it does not independently prove causation, coordination, alliance, or responsibility.',
        'nodes': nodes[:100],
        'edges': edges[:500],
    }

    if len(payload['nodes']) < 10:
        raise SystemExit(f'RENDER BLOCKED: graph has only {len(payload["nodes"])} nodes')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    print(f'Published Intelligence Web artifact: {len(payload["nodes"])} ranked nodes / {len(payload["edges"])} evidence-backed edges')


if __name__ == '__main__':
    main()
