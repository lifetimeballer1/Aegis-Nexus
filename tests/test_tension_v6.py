"""B23/B26 — Tension v6 story pressure, early warning and history contracts."""
from datetime import datetime, timedelta, timezone

import build_tension as bt

NOW = datetime.now(timezone.utc)
ISO = NOW.isoformat().replace('+00:00', 'Z')


def story(contribution, severity='critical', status='active', age_hours=1):
    stamp = (NOW - timedelta(hours=age_hours)).isoformat().replace('+00:00', 'Z')
    return {'id': f'story-{contribution}-{age_hours}', 'title': 'Story', 'severity': severity, 'status': status,
            'lastUpdated': stamp, 'tensionContribution': contribution}


def test_story_pressure_is_capped_and_audited():
    stories = [story(90) for _ in range(20)]
    pressure, audit = bt.compute_story_pressure(stories, NOW)
    assert pressure == bt.STORY_PRESSURE_CAP
    assert len(audit) == bt.STORY_PRESSURE_TOP
    assert audit[0]['contribution'] == 90.0


def test_eligible_stories_filters_dormant_old_and_low():
    stories = [
        story(80, severity='critical', status='active', age_hours=2),
        story(80, severity='critical', status='dormant'),
        story(80, severity='low'),
        story(80, severity='high', age_hours=100),
    ]
    eligible = bt.eligible_stories({'stories': stories}, NOW)
    assert len(eligible) == 1
    assert eligible[0]['severity'] == 'critical'


def test_early_warning_levels_and_summary():
    breakdown = {'Military posture': 60, 'Conflict activity': 50}
    watch = bt.build_early_warning(30, breakdown, [], [])
    assert watch['level'] == 'WATCH'
    critical = bt.build_early_warning(80, breakdown, [], [{'title': 'Top story', 'contribution': 40}])
    assert critical['level'] == 'HIGH'
    assert 'Top story' in critical['summary']
    assert critical['strongestDriver'] == 'Military posture'


def test_history_prunes_other_writers():
    history = [
        {'updatedAt': '2026-09-01T00:00:00Z', 'tension': 74, 'scoreVersion': 5},
        {'updatedAt': '2026-09-02T00:00:00Z', 'tension': 41, 'scoreVersion': 5},
        {'updatedAt': '2026-09-03T00:00:00Z', 'tension': 45, 'scoreVersion': 6},
    ]
    pruned = bt.prune_history(history)
    assert len(pruned) == 1
    assert pruned[0]['tension'] == 45
