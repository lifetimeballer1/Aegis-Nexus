#!/usr/bin/env python3
"""Validate the published Intelligence Web graph contract."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GRAPH = ROOT / 'data' / 'intelligence_graph.json'


def main():
    graph = json.loads(GRAPH.read_text(encoding='utf-8'))
    nodes = graph.get('nodes')
    edges = graph.get('edges')
    assert isinstance(nodes, list) and nodes, 'graph nodes missing'
    assert isinstance(edges, list), 'graph edges missing'

    ids = [str(n.get('id')) for n in nodes]
    assert all(n and n != 'None' for n in ids), 'node id missing'
    assert len(ids) == len(set(ids)), 'duplicate node ids'
    valid = set(ids)

    for node in nodes:
        assert node.get('label'), f"node {node.get('id')} missing label"
        assert isinstance(node.get('evidence'), list), f"node {node.get('id')} evidence missing"
        assert 0 <= float(node.get('importance', 0) or 0), f"node {node.get('id')} invalid importance"

    pairs = set()
    for edge in edges:
        source, target = str(edge.get('source')), str(edge.get('target'))
        assert source in valid and target in valid, 'edge endpoint not in nodes'
        assert source != target, 'self-loop is not allowed in published graph'
        evidence = edge.get('evidence')
        assert isinstance(evidence, list) and evidence, 'published edge must retain evidence'
        relationship = str(edge.get('relationship') or '').strip()
        assert relationship, 'edge relationship missing'
        pair = (source, relationship, target)
        assert pair not in pairs, f'duplicate relationship claim: {pair}'
        pairs.add(pair)
        assert int(edge.get('evidenceCount', 0) or 0) >= 1, 'edge evidenceCount missing'

    print(f'PASS intelligence graph contract: {len(nodes)} nodes / {len(edges)} evidence-backed edges')


if __name__ == '__main__':
    main()
