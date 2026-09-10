"""B20 — story fusion and gap lifecycle contracts."""
import build_brain_stories as bbs

NOW = '2026-09-10T12:00:00Z'


def story_fixture(**over):
    base = {
        'id': 'story-test',
        'eventId': 'evt-1',
        'title': 'Missile attack reported on port',
        'severity': 'critical',
        'lastUpdated': NOW,
        'status': 'active',
        'slots': {'actor': True, 'target': False, 'geo': True, 'time': True, 'outcome': False, 'corroboration': False, 'assessment': False},
        'evidence': [{'title': 'Report', 'url': 'https://example.org/a', 'source': 'example.org', 'time': NOW, 'sourceClass': ''}],
    }
    base.update(over)
    return base


def test_gap_ids_are_stable():
    assert bbs.stable_id('gap', 'story-1', 'no_target') == bbs.stable_id('gap', 'story-1', 'no_target')
    assert bbs.stable_id('gap', 'story-1', 'no_target') != bbs.stable_id('gap', 'story-2', 'no_target')


def test_derive_gaps_is_evidence_bounded():
    gaps = bbs.derive_gaps(story_fixture(), None, {'independentReportingGroups': 0, 'sourceIndependence': 'low'}, {}, {'resolution': {}})
    types = {g['type'] for g in gaps}
    assert 'no_target' in types
    assert 'single_source' in types
    assert 'no_primary' in types
    assert 'no_assessment' in types
    for gap in gaps:
        assert gap['storyId'] == 'story-test'
        assert gap['evidenceNeeded']
        assert gap['_urls']


def test_lifecycle_preserves_opened_at_and_detects_reopen():
    prior = {'gap-x': {'id': 'gap-x', 'storyId': 'story-test', 'type': 'no_target', 'severity': 'high', 'state': 'closed', 'openedAt': '2026-09-01T00:00:00Z', 'updatedAt': '2026-09-02T00:00:00Z'}}
    current = [{'id': 'gap-x', 'storyId': 'story-test', 'type': 'no_target', 'severity': 'high', 'evidenceNeeded': 'target'}]
    [gap] = bbs.lifecycle(current, prior, NOW)
    assert gap['state'] == 'open'
    assert gap['openedAt'] == '2026-09-01T00:00:00Z'


def test_close_gap_carries_closing_evidence():
    prior = {'id': 'gap-y', 'storyId': 'story-test', 'type': 'single_source', 'severity': 'high', 'state': 'open', 'openedAt': '2026-09-01T00:00:00Z', 'evidenceNeeded': 'two independent groups'}
    closed = bbs.close_gap(prior, story_fixture(), NOW)
    assert closed['state'] == 'closed'
    assert closed['resolvedAt'] == NOW
    assert closed['closingEvidence']


def test_pressure_is_bounded_and_gap_sensitive():
    low = bbs.pressure(story_fixture(severity='low', slots={'actor': True, 'target': True, 'geo': True, 'time': True, 'outcome': True, 'corroboration': True, 'assessment': True}), [])
    high = bbs.pressure(story_fixture(), ['critical', 'high'])
    assert 0 <= low <= 100 and 0 <= high <= 100
    assert high > low
