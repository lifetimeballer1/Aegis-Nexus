"""Event-export freshness contracts (2026-09-14 stale-export rewire).

Live readers (timeline, map signals, top signals) consume live_events.json,
event_history.json and historical_trends.json, but no refresh step wrote them —
headers stamped fresh times while content rotted ("Updated 4d ago", "24H cannot
be resolved", "8d ago" signals). These tests FAIL if the exports go stale again:

- wiring: the three builder steps + artifacts must be present in refresh_pipeline.py
- functional: each builder advances its export (updatedAt/observations/samples)
  when run against fixture inputs, and refuses to overwrite on empty input.
"""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

NOW = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _fresh_stamp(payload, field='updatedAt', max_age_s=120):
    stamp = payload.get(field)
    assert stamp, f'missing {field}'
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))).total_seconds()
    assert -120 < age < max_age_s, f'{field} stale: age={age:.0f}s'


def _stories(n=6):
    return [{'title': f'Test signal event number {i} in Ukraine region conflict',
             'url': f'https://example.test/story-{i}',
             'publishedAt': NOW, 'published_date': NOW,
             'source': 'example.test'} for i in range(n)]


def test_pipeline_wires_event_export_regeneration():
    import refresh_pipeline as pipeline
    for script in ('build_live_events.py', 'build_event_history.py', 'build_historical_trends.py'):
        assert script in (ROOT / 'refresh_pipeline.py').read_text(encoding='utf-8'), \
            f'{script} not wired into refresh_pipeline.py — exports will rot again'
    for artifact in ('live_events.json', 'event_history.json', 'historical_trends.json'):
        assert artifact in pipeline.REQUIRED_ARTIFACTS, \
            f'{artifact} missing from REQUIRED_ARTIFACTS manifest gate'


def test_live_events_advances_on_fresh_snapshot(tmp_path):
    import build_live_events as builder
    (tmp_path / 'snapshot.json').write_text(json.dumps({'stories': _stories()}), encoding='utf-8')
    first = builder.main(data_dir=tmp_path)
    assert len(first['events']) >= 1
    _fresh_stamp(first)
    # New story joins the feed -> rebuild must pick it up, never serve the old set.
    snap = json.loads((tmp_path / 'snapshot.json').read_text(encoding='utf-8'))
    snap['stories'].append({'title': 'Brand new diplomatic summit agreement signed today',
                            'url': 'https://example.test/brand-new',
                            'publishedAt': NOW, 'published_date': NOW, 'source': 'example.test'})
    (tmp_path / 'snapshot.json').write_text(json.dumps(snap), encoding='utf-8')
    second = builder.main(data_dir=tmp_path)
    _fresh_stamp(second)
    assert not (tmp_path / 'live_events.json.tmp').exists(), 'atomic swap left a tmp file'
    titles = [e['title'] for e in second['events']]
    assert any('Brand new' in t for t in titles), 'rebuild ignored fresh snapshot stories'


def test_live_events_refuses_empty_snapshot(tmp_path):
    import build_live_events as builder
    (tmp_path / 'snapshot.json').write_text(json.dumps({'stories': []}), encoding='utf-8')
    with pytest.raises(SystemExit):
        builder.main(data_dir=tmp_path)
    assert not (tmp_path / 'live_events.json').exists(), 'empty build must not create output'


def _live_events_payload(n=4):
    return {'updatedAt': NOW, 'events': [
        {'title': f'History probe event {i} Sudan region crisis', 'category': 'conflict',
         'confidence': 'moderate', 'reportCount': 2 + i, 'sourceCount': 2,
         'sources': ['a.test', 'b.test'], 'anchors': [f'probe-region-{i}'],
         'firstSeen': NOW, 'lastSeen': NOW,
         'urls': [f'https://example.test/h{i}']} for i in range(n)]}


def test_event_history_appends_fresh_observations(tmp_path):
    import build_event_history as history
    (tmp_path / 'live_events.json').write_text(json.dumps(_live_events_payload()), encoding='utf-8')
    first = history.main(data_dir=tmp_path)
    assert len(first['events']) >= 1
    _fresh_stamp(first)
    obs_before = {k: len(v['observations']) for k, v in first['events'].items()}
    assert all(c >= 1 for c in obs_before.values())
    # Material change (reportCount bump) -> a NEW observation must be appended.
    payload = _live_events_payload()
    for e in payload['events']:
        e['reportCount'] += 5
    (tmp_path / 'live_events.json').write_text(json.dumps(payload), encoding='utf-8')
    second = history.main(data_dir=tmp_path)
    _fresh_stamp(second)
    for key, count in obs_before.items():
        assert len(second['events'][key]['observations']) == count + 1, \
            'event-history run added no fresh observation — timeline would rot'
    assert not (tmp_path / 'event_history.json.tmp').exists(), 'atomic swap left a tmp file'


def test_event_history_refuses_missing_input(tmp_path):
    import build_event_history as history
    with pytest.raises(SystemExit):
        history.main(data_dir=tmp_path)
    assert not (tmp_path / 'event_history.json').exists()


def test_trends_record_sample_and_advance(tmp_path):
    import build_historical_trends as trends
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat().replace('+00:00', 'Z')
    (tmp_path / 'history.json').write_text(
        json.dumps([{'updatedAt': old, 'tension': 40, 'delta': 0, 'scoreVersion': 5}]), encoding='utf-8')
    (tmp_path / 'snapshot.json').write_text(
        json.dumps({'tension': 44, 'tensionDelta': 4, 'scoreVersion': 5}), encoding='utf-8')
    out = trends.main(data_dir=tmp_path)
    _fresh_stamp(out)
    rows = json.loads((tmp_path / 'history.json').read_text(encoding='utf-8'))
    assert rows[-1]['tension'] == 44, 'fresh snapshot tension never recorded'
    assert out['series'][-1]['tension'] == 44, 'trends series does not end at live tension'
    assert not (tmp_path / 'historical_trends.json.tmp').exists()
    # Immediate re-run must not duplicate the sample.
    trends.main(data_dir=tmp_path)
    rows2 = json.loads((tmp_path / 'history.json').read_text(encoding='utf-8'))
    assert len(rows2) == len(rows), 'duplicate tension sample on re-run'


def test_trends_refuse_missing_snapshot_tension(tmp_path):
    import build_historical_trends as trends
    (tmp_path / 'snapshot.json').write_text(json.dumps({'stories': []}), encoding='utf-8')
    with pytest.raises((SystemExit, ValueError)):
        trends.main(data_dir=tmp_path)
