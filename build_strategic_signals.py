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


def infer_category(evidence: list[dict], actions: list[dict]) -> str:
    counts = Counter()
    for action in actions:
        category = str(action.get('category') or '').strip().lower()
        if category:
            counts[category] += 2
    for item in evidence:
        text = f"{item.get('title') or ''} {item.get('source') or ''}".lower()
        for category, pattern in CATEGORY_PATTERNS.items():
            if re.search(pattern, text, re.I):
                counts[category] += 1
    return counts.most_common(1)[0][0] if counts else 'general'


def main() -> int:
    brain = json.loads(INPUT.read_text(encoding='utf-8'))
    signals = []
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    nodes_by_actor = {node.get('label'): node for node in brain.get('nodes', []) if isinstance(node, dict)}
    for actor in MAJOR_ACTORS:
        node = nodes_by_actor.get(actor)
        if not node:
            continue

        actions = [a for a in (node.get('actions') or []) if isinstance(a, dict)]
        evidence = evidence_from_node(node)
        categories = Counter()
        targets = Counter()

        for action in actions:
            category = str(action.get('category') or '').strip().lower()
            if category:
                categories[category] += 1
            target = str(action.get('target') or '').strip()
            if target:
                targets[target] += 1

        # The Brain can contain strong source-backed evidence even when its
        # action enrichment layer has no structured actions. Do not turn that
        # into a false "no signal" state. Instead emit a conservative
        # evidence-activity signal and preserve the underlying evidence.
        if not evidence:
            continue

        if not categories:
            category = infer_category(evidence, actions)
            categories[category] = 1
        else:
            category = categories.most_common(1)[0][0]

        dominant_target, target_count = targets.most_common(1)[0] if targets else ('', 0)
        action_count = len(actions)
        category_count = categories[category]
        intensity = min(100, action_count * 10 + category_count * 5 + target_count * 5 + min(30, len(evidence)))

        signal_text = (
            f'{actor} shows source-backed {category} activity'
            if action_count
            else f'{actor} has source-backed intelligence activity'
        )
        signals.append({
            'actor': actor,
            'signal': signal_text,
            'category': category,
            'dominantTarget': dominant_target,
            'actionCount': action_count,
            'categoryCount': category_count,
            'targetCount': target_count,
            'intensity': intensity,
            'evidence': evidence[:20],
            'sourceBacked': True,
        })

    result = {
        'version': 2,
        'generatedAt': now,
        'sourceBackedOnly': True,
        'signals': signals,
        'majorActorCoverage': {actor: any(s['actor'] == actor for s in signals) for actor in MAJOR_ACTORS},
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'PASS: strategic signals={len(signals)} coverage={result["majorActorCoverage"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
