#!/usr/bin/env python3
"""Publish the Intelligence Web artifact from the authoritative snapshot.

The graph is a presentation projection of canonical intelligence. Preserve
source metadata so the Web can render intelligence context without creating a
second source of truth or inventing relationships.
"""
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / 'data' / 'snapshot.json'
OUT = ROOT / 'data' / 'intelligence_graph.json'

# Presentation-layer quality rules for the Intelligence Web projection.
# These filter/demote noisy entities at publish time only; upstream source
# data files (snapshot.json, canonical intelligence) are never modified.
MAX_NODES = 60
MAX_EDGES = 300

# Publisher/source names that leaked into entity labels: never entities.
PUBLISHER_SUBSTRINGS = ('yahoo finance', 'ndtv profit', 'devdiscourse')

# Headline-fragment leads: entity extractor caught a headline, not an entity.
JUNK_LEAD = re.compile(
    r'^(why|how|what|review|remark|raise|ministry condemned|'
    r'secretary visits|justice\b.*\bgroup|jordan iran|missile threat)\b',
    re.IGNORECASE,
)

# Substrings marking extractor noise (compound fragments, headline text).
# Applied only to low-cardinality kinds so real orgs/countries never match.
JUNK_SUBSTRINGS = ('friendship group', ' and ', ' near ', ' threat and ')
JUNK_SUBSTR_KINDS = {'location', 'company', 'person', 'region'}

# Explicit merge map: normalized label -> (canonical id-hint label, kind).
# Collapses duplicate/possessive/truncated variants of the same real entity.
ALIAS_CANONICAL = {
    'west bank': ('West Bank', 'region'),
    'in west bank': ('West Bank', 'region'),
    'israeli west bank': ('West Bank', 'region'),
    'palestinian west bank': ('West Bank', 'region'),
    'uk west bank': ('West Bank', 'region'),
    'uks west bank': ('West Bank', 'region'),
    'mandeb strait': ('Bab-el-Mandeb Strait', 'location'),
    'mandab strait': ('Bab-el-Mandeb Strait', 'location'),
    'bab el mandeb strait': ('Bab-el-Mandeb Strait', 'location'),
    'president donald trump': ('President Donald Trump', 'person'),
    'president donald trump s': ('President Donald Trump', 'person'),
    'president vladimir putin': ('President Vladimir Putin', 'person'),
    'president putin': ('President Vladimir Putin', 'person'),
    'minister ed miliband': ('Ed Miliband', 'person'),
    'secretary ed miliband': ('Ed Miliband', 'person'),
    'minister ed': ('Ed Miliband', 'person'),
    'kalayaan group': ('Kalayaan Islands', 'location'),
    'kalayaan island group': ('Kalayaan Islands', 'location'),
    'kalayaan island': ('Kalayaan Islands', 'location'),
    'the virgin islands': ('Virgin Islands', 'location'),
    'caribbean the virgin islands': ('Virgin Islands', 'location'),
}

# Kind corrections for systematically misclassified entities.
KIND_FIX = {
    'west bank': 'region',
}

# Ranking priority: countries, conflicts, economics first; trivia last.
KIND_PRIORITY_BONUS = {
    'country': 25,
    'conflict': 25,
    'company': 8,
    'financial_institution': 8,
    'military': 10,
    'military_command': 10,
    'intelligence': 10,
    'armed_group': 10,
    'government': 10,
    'government_agency': 10,
    'international_organization': 10,
}

# Quality gate: entities this weak are noise unless structurally important.
GATE_MENTIONS = 2
GATE_DEGREE = 1
GATE_EXEMPT_KINDS = {
    'country', 'conflict', 'military', 'military_command', 'intelligence',
    'armed_group', 'government', 'government_agency',
    'international_organization',
}


def normalize_label(label):
    text = str(label or '').lower().replace('\u2019', "'").replace('\u2018', "'")
    text = re.sub(r"'s\b", '', text)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^(the|in|a|an)\s+', '', text)
    return text

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
    priority = KIND_PRIORITY_BONUS.get(str(node.get('kind') or '').lower(), 0)
    return (int(node.get('mentions') or 0) * 2 + math.log1p(len(evidence)) * 8
            + _recency_score(node) + breaking + priority)


def is_noise_label(label, kind=''):
    lowered = str(label or '').lower()
    if any(pub in lowered for pub in PUBLISHER_SUBSTRINGS):
        return True
    if JUNK_LEAD.match(str(label or '').strip()):
        return True
    if str(kind or '').lower() in JUNK_SUBSTR_KINDS:
        return any(sub in lowered for sub in JUNK_SUBSTRINGS)
    return False


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
    staged = []
    for raw in raw_nodes:
        label = str(raw.get('label') or raw.get('name') or raw.get('canonical_name') or raw.get('id'))
        kind = str(raw.get('kind') or raw.get('type') or raw.get('entity_type') or 'actor')
        if is_noise_label(label, kind):
            continue
        node = _copy_known_fields(raw, NODE_FIELDS)
        node['id'] = str(raw.get('id'))
        node['label'] = label
        node['kind'] = str(raw.get('kind') or raw.get('type') or raw.get('entity_type') or 'actor')
        node['mentions'] = int(raw.get('mentions') or 0)
        node['evidence'] = [e for e in (raw.get('evidence') or [])[:12] if isinstance(e, dict)]
        staged.append(node)

    # Merge duplicate variants (possessives, truncations, renames) so each
    # real-world entity renders as ONE dot instead of several floating dots.
    groups = {}
    for node in staged:
        norm = normalize_label(node['label'])
        alias = ALIAS_CANONICAL.get(norm)
        key = alias[0].lower() if alias else (norm or node['id'])
        groups.setdefault(key, []).append(node)

    nodes = []
    for key, members in groups.items():
        members.sort(key=lambda n: (n['mentions'], len(n.get('evidence') or [])), reverse=True)
        winner = dict(members[0])
        alias = ALIAS_CANONICAL.get(normalize_label(winner['label']))
        if alias:
            winner['label'], winner['kind'] = alias[0], alias[1]
        norm = normalize_label(winner['label'])
        if norm in KIND_FIX:
            winner['kind'] = KIND_FIX[norm]
        seen_ev, merged_ev = set(), []
        for member in members:
            for ev in member.get('evidence') or []:
                sig = (str(ev.get('title') or ''), str(ev.get('url') or ev.get('link') or ''))
                if sig not in seen_ev:
                    seen_ev.add(sig)
                    merged_ev.append(ev)
        winner['mentions'] = sum(int(m.get('mentions') or 0) for m in members)
        winner['evidence'] = merged_ev[:12]
        winner['merged_from'] = len(members)
        nodes.append(winner)

    valid = {n['id'] for n in nodes}
    label_to_id = {}
    for node in nodes:
        for label in (node.get('label'), node.get('name'), node.get('canonical_name')):
            if label:
                label_to_id[str(label).strip().lower()] = node['id']
    # Variant spellings found in edges must resolve to the merged node.
    for raw in raw_nodes:
        for label in (raw.get('label'), raw.get('name'), raw.get('canonical_name')):
            if not label:
                continue
            norm = normalize_label(label)
            alias = ALIAS_CANONICAL.get(norm)
            if alias:
                label_to_id[str(label).strip().lower()] = label_to_id.get(alias[0].lower(), label_to_id.get(str(label).strip().lower()))
            elif norm:
                for node in nodes:
                    if normalize_label(node['label']) == norm:
                        label_to_id[str(label).strip().lower()] = node['id']
                        break
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

    # Quality gate to fixpoint: drop weak, unconnected trivia and any node
    # left with zero edges (a dot with no lines is the floating-dot bug).
    # Degrees are recomputed each pass so junk clusters collapse together.
    for _ in range(10):
        degree = {node['id']: 0 for node in nodes}
        for edge in edges:
            if edge['source'] in degree:
                degree[edge['source']] += 1
            if edge['target'] in degree:
                degree[edge['target']] += 1
        gated = []
        for node in nodes:
            deg = degree[node['id']]
            if deg == 0:
                continue
            kind = str(node.get('kind') or '').lower()
            if kind in GATE_EXEMPT_KINDS:
                gated.append(node)
                continue
            # Countries/conflicts/economics stay; trivia needs real weight:
            # at least 2 mentions AND at least 2 evidence-backed connections.
            if int(node.get('mentions') or 0) >= GATE_MENTIONS and deg > GATE_DEGREE:
                gated.append(node)
        if len(gated) == len(nodes):
            break
        nodes = gated
        valid = {n['id'] for n in nodes}
        edges = [e for e in edges if e['source'] in valid and e['target'] in valid]
    valid = {n['id'] for n in nodes}
    edges = [e for e in edges if e['source'] in valid and e['target'] in valid]
    for node in nodes:
        node['importance'] = round(max(float(node.get('importance') or 0), node_rank(node)) + degree[node['id']] * 5, 3)

    nodes.sort(key=lambda n: (n['importance'], n['mentions'], n['label']), reverse=True)
    edges.sort(key=lambda e: (e['weight'], e['evidenceCount']), reverse=True)
    published_ids = {node['id'] for node in nodes[:MAX_NODES]}
    edges = [edge for edge in edges if edge['source'] in published_ids and edge['target'] in published_ids]

    payload = {
        'updatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'method': graph.get('method') or 'Evidence-backed public reporting graph',
        'caution': graph.get('caution') or 'A connection means the entities share a public evidence record; it does not independently prove causation, coordination, alliance, or responsibility.',
        'nodes': nodes[:MAX_NODES],
        'edges': edges[:MAX_EDGES],
    }

    if len(payload['nodes']) < 10:
        raise SystemExit(f'RENDER BLOCKED: graph has only {len(payload["nodes"])} nodes')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    print(f'Published Intelligence Web artifact: {len(payload["nodes"])} ranked nodes / {len(payload["edges"])} evidence-backed edges')


if __name__ == '__main__':
    main()
