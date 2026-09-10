#!/usr/bin/env python3
"""Build evidence-backed strategic signals from the canonical Intelligence Brain."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DATA = Path('data')
INPUT = DATA / 'intelligence_brain.json'
OUTPUT = DATA / 'strategic_signals.json'

MAJOR_ACTORS = ('United States', 'China')
MAX_SECONDARY = 6
SECONDARY_MIN_EVIDENCE = 10
CATEGORY_PATTERNS = {
    'military': r'\b(military|defense|defence|troops|forces|missile|strike|deployment|navy|army|air force)\b',
    'diplomatic': r'\b(diplomat|diplomatic|talks|negotiat|summit|ambassador|foreign minister)\b',
    'economic': r'\b(econom|tariff|trade|investment|finance|interest rate|sanction|sanctions)\b',
    'technology': r'\b(technology|tech|semiconductor|chip|chips|ai|artificial intelligence|cyber)\b',
    'energy': r'\b(energy|oil|gas|lng|nuclear|uranium|electricity)\b',
    'political': r'\b(president|congress|parliament|election|government|policy|political)\b',
}


def evidence_from_node(node: dict) -> list[dict]:
    """Collect valid node evidence while preserving source attribution."""
    result = []
    seen = set()
    for item in node.get('evidence') or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get('url') or '').strip()
        source = str(item.get('source') or '').strip()
        if not url and not source:
            continue
        key = url or f"{source}|{item.get('title') or ''}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def flatten_actions(node: dict) -> tuple[list[dict], Counter]:
    """Handle both action shapes honestly.

    enrich_brain_actions.py writes node['actions'] as a dict of
    {category: [evidence,...]}. Older runs wrote a flat list of action
    dicts with 'category'/'target' keys. Flatten either form without
    inventing actions.
    """
    raw = node.get('actions')
    flat: list[dict] = []
    categories = Counter()
    if isinstance(raw, dict):
        for category, items in raw.items():
            cat = str(category or '').strip().lower()
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    entry = dict(item)
                    if cat and not entry.get('category'):
                        entry['category'] = cat
                    flat.append(entry)
            if cat:
                categories[cat] += len([x for x in items if isinstance(x, dict)])
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            flat.append(item)
            cat = str(item.get('category') or '').strip().lower()
            if cat:
                categories[cat] += 1
    return flat, categories


def infer_category(evidence: list[dict], actions: list[dict], seeded: Counter) -> str:
    counts = Counter(seeded)
    for action in actions:
        category = str(action.get('category') or '').strip().lower()
        if category and category not in seeded:
            counts[category] += 2
    for item in evidence:
        text = f"{item.get('title') or ''} {item.get('source') or ''}".lower()
        for category, pattern in CATEGORY_PATTERNS.items():
            if re.search(pattern, text, re.I):
                counts[category] += 1
    return counts.most_common(1)[0][0] if counts else 'general'


def last_evidence_time(evidence: list[dict]) -> str:
    latest = ''
    for item in evidence:
        stamp = str(item.get('time') or item.get('publishedAt') or '')
        if stamp and stamp > latest:
            latest = stamp
    return latest


def build_signal(actor: str, node: dict) -> dict | None:
    actions, seeded_categories = flatten_actions(node)
    evidence = evidence_from_node(node)
    # The Brain can contain strong source-backed evidence even when its
    # action enrichment layer has no structured actions. Do not turn that
    # into a false "no signal" state. Instead emit a conservative
    # evidence-activity signal and preserve the underlying evidence.
    if not evidence:
        return None
    categories = Counter(seeded_categories)
    targets = Counter()
    for action in actions:
        target = str(action.get('target') or '').strip()
        if target:
            targets[target] += 1
    # Co-mention targets are honest co-occurrence volumes from the action
    # layer, not claims of direction or causality.
    for entry in (node.get('actionTargets') or [])[:20]:
        if not isinstance(entry, dict):
            continue
        target = str(entry.get('target') or '').strip()
        count = int(entry.get('coMentions') or 0)
        if target and target != actor and count > 0:
            targets[target] += count
    category = infer_category(evidence, actions, categories)
    if not categories:
        categories[category] = 1
    dominant_target, target_count = targets.most_common(1)[0] if targets else ('', 0)
    action_count = len(actions)
    category_count = categories[category]
    intensity = min(100, action_count * 2 + category_count * 5 + target_count * 2 + min(30, len(evidence)))
    signal_text = (
        f'{actor} shows source-backed {category} activity'
        if action_count
        else f'{actor} has source-backed intelligence activity'
    )
    top_targets = [{'target': t, 'mentions': c} for t, c in targets.most_common(5)]
    return {
        'actor': actor,
        'signal': signal_text,
        'category': category,
        'categories': dict(categories.most_common(8)),
        'dominantTarget': dominant_target,
        'topTargets': top_targets,
        'actionCount': action_count,
        'actionEvidenceCount': int(node.get('actionEvidenceCount') or action_count),
        'categoryCount': category_count,
        'targetCount': target_count,
        'evidenceCount': len(evidence),
        'lastEvidenceTime': last_evidence_time(evidence),
        'intensity': intensity,
        'evidence': evidence[:20],
        'sourceBacked': True,
    }


def main() -> int:
    brain = json.loads(INPUT.read_text(encoding='utf-8'))
    signals = []
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    nodes_by_actor = {node.get('label'): node for node in brain.get('nodes', []) if isinstance(node, dict)}
    for actor in MAJOR_ACTORS:
        node = nodes_by_actor.get(actor)
        if not node:
            continue
        signal = build_signal(actor, node)
        if signal:
            signals.append(signal)

    # Honest enrichment: other Brain hubs already carry 10+ source-backed
    # evidence items but never surfaced as signals, leaving signal lists
    # sparse. Emit capped secondary signals from that existing evidence.
    secondaries = []
    for label, node in nodes_by_actor.items():
        if label in MAJOR_ACTORS:
            continue
        evidence = evidence_from_node(node)
        if len(evidence) < SECONDARY_MIN_EVIDENCE:
            continue
        signal = build_signal(label, node)
        if signal:
            secondaries.append(signal)
    secondaries.sort(key=lambda s: (s['evidenceCount'], s['intensity']), reverse=True)
    signals.extend(secondaries[:MAX_SECONDARY])

    result = {
        'version': 3,
        'generatedAt': now,
        'sourceBackedOnly': True,
        'method': 'Source-backed Brain evidence plus dict/list action layers; co-mention targets are co-occurrence volumes, not causality.',
        'signals': signals,
        'majorActorCoverage': {actor: any(s['actor'] == actor for s in signals) for actor in MAJOR_ACTORS},
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'PASS: strategic signals={len(signals)} coverage={result["majorActorCoverage"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
