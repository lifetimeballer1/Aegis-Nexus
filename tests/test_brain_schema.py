"""B3/B4 — story + gap schema contracts."""
from brain_schema import validate_stories, validate_gap_history

NOW = '2026-09-10T12:00:00Z'


def story(**over):
    base = {
        'id': 'story-1',
        'title': 'Escalation in the Red Sea',
        'kind': 'conflict',
        'severity': 'critical',
        'confidence': 'moderate',
        'status': 'active',
        'firstSeen': NOW,
        'lastUpdated': NOW,
        'completeness': 0.6,
        'slots': {'actor': True, 'target': False, 'geo': True, 'time': True, 'outcome': False, 'corroboration': True, 'assessment': False},
        'evidence': [{'title': 'Public report', 'url': 'https://example.org/a', 'source': 'example.org', 'time': NOW}],
        'gapIds': ['gap-1'],
    }
    base.update(over)
    return base


def gap(**over):
    base = {
        'id': 'gap-1',
        'storyId': 'story-1',
        'type': 'no_target',
        'severity': 'high',
        'state': 'open',
        'openedAt': NOW,
        'updatedAt': NOW,
        'evidenceNeeded': 'A named target role for the reported action',
    }
    base.update(over)
    return base


def document(stories=None, gaps=None):
    stories = stories if stories is not None else [story()]
    gaps = gaps if gaps is not None else [gap()]
    return {
        'version': 1,
        'updatedAt': NOW,
        'sourceBackedOnly': True,
        'stories': stories,
        'gaps': gaps,
        'stats': {
            'stories': len(stories),
            'open': sum(1 for g in gaps if g.get('state') == 'open'),
            'narrowing': sum(1 for g in gaps if g.get('state') == 'narrowing'),
            'closed': sum(1 for g in gaps if g.get('state') == 'closed'),
            'withGaps': sum(1 for s in stories if s.get('gapIds')),
        },
    }


def test_valid_document_passes():
    assert validate_stories(document()) == []


def test_story_requires_evidence_and_valid_enums():
    bad = document(stories=[story(evidence=[])], gaps=[])
    errors = validate_stories(bad)
    assert any('evidence' in e for e in errors)
    bad = document(stories=[story(severity='urgent')], gaps=[])
    assert any('severity' in e for e in validate_stories(bad))


def test_gap_references_and_closed_requirements():
    bad = document(gaps=[gap(storyId='missing')])
    assert any('storyId' in e for e in validate_stories(bad))
    closed = gap(state='closed', resolvedAt=NOW, closingEvidence=[{'title': 'Resolution report', 'url': 'https://example.org/b'}])
    assert validate_stories(document(gaps=[closed])) == []
    broken = gap(state='closed')
    assert any('resolvedAt' in e for e in validate_stories(document(gaps=[broken])))


def test_gap_history_contract():
    doc = {
        'version': 1,
        'updatedAt': NOW,
        'cycles': [{'at': NOW, 'stories': 1, 'open': 1, 'narrowing': 0, 'closed': 0, 'opened': ['gap-1'], 'closedNow': [], 'reopened': []}],
        'gaps': {'gap-1': {'storyId': 'story-1', 'type': 'no_target', 'state': 'open', 'openedAt': NOW, 'resolvedAt': None, 'history': [{'at': NOW, 'state': 'open'}]}},
    }
    assert validate_gap_history(doc) == []
    doc['gaps']['gap-1']['state'] = 'closed'
    assert any('resolvedAt' in e for e in validate_gap_history(doc))
