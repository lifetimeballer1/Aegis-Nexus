"""Tension anti-fossil contracts (2026-09-14 tension-unfreeze fix).

Snapshot tension rotted at 41 (~Sept 6 2026): no pipeline step recomputed it,
stories were rewritten while tension/breakdownScores carried forward verbatim,
and ~68% of stories (sourceType fallback-news) matched NONE of the driver
eligible sets. These tests FAIL on that pattern:

- wiring: recompute_tension.py runs AFTER source_failover.py (all story
  mutators) and BEFORE build_historical_trends.py (trends sampler).
- eligibility: all-fallback-news stories with conflict signal move the
  Conflict driver off its base (old sets: empty pool -> flat base score).
- no-verbatim-carry: changed stories change tension; calm stories make it
  FALL and hot stories make it RISE (ratchet-only recalibrate cannot fall).
"""
import copy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
FOSSIL_TENSION = 41


def _story(title, source_type='fallback-news', label='Fallback'):
    return {'id': title[:12], 'title': title, 'summary': title,
            'sourceType': source_type, 'sourceLabel': label,
            'url': 'https://example.test/' + str(abs(hash(title)) % 999999),
            'source': 'https://example.test', 'time': NOW}


def _hot_stories(n=12):
    return [_story(f'War offensive {i}: airstrike missile drone troops invasion shelling battle')
            for i in range(n)]


def _calm_stories(n=12):
    return [_story(f'Community garden festival celebrates spring flowers number {i}')
            for i in range(n)]


def _snapshot(stories, tension=FOSSIL_TENSION):
    return {'updatedAt': NOW, 'scoreVersion': 5, 'tension': tension,
            'tensionDelta': 0,
            'breakdownScores': {k: tension for k in
                                      ('Conflict activity', 'Diplomatic strain', 'Economic pressure',
                                       'Market volatility', 'Military posture',
                                       'Climate & humanitarian pressure')},
            'stories': stories}


def test_pipeline_wires_tension_recompute_after_story_mutators():
    text = (ROOT / 'refresh_pipeline.py').read_text(encoding='utf-8')
    assert 'recompute_tension.py' in text, 'tension recompute step missing from pipeline'
    assert text.index('source_failover.py') < text.index('recompute_tension.py') < \
        text.index('build_historical_trends.py'), \
        'recompute must run after story mutators, before trends sampler'


def test_fallback_news_stories_drive_conflict_score():
    import recompute_tension as rt
    snap = _snapshot(_hot_stories())
    rt.recompute(snap, [])
    assert snap['driverSignals']['Conflict activity']['poolSize'] == 12, \
        'fallback-news stories invisible to Conflict driver'
    assert snap['breakdownScores']['Conflict activity'] > 35, \
        'conflict signal in fallback-news stories did not move the driver off base'


def test_changed_stories_change_tension_not_verbatim():
    import recompute_tension as rt
    first = _snapshot(_hot_stories())
    rt.recompute(first, [])
    second = _snapshot(_calm_stories(), tension=first['tension'])
    second['breakdownScores'] = copy.deepcopy(first['breakdownScores'])
    rt.recompute(second, [])
    assert second['tension'] != first['tension'], \
        'tension carried verbatim across changed stories (fossil pattern)'
    expected = round(sum(second['breakdownScores'][k] * rt.WEIGHTS[k] for k in rt.WEIGHTS))
    assert second['tension'] == expected, 'tension is not a function of current drivers'


def test_tension_falls_on_calm_stories_and_rises_on_hot():
    import recompute_tension as rt
    calm = _snapshot(_calm_stories())
    rt.recompute(calm, [])
    assert calm['tension'] < FOSSIL_TENSION, \
        f"calm stories must lower tension below fossil {FOSSIL_TENSION}, got {calm['tension']}"
    hot = _snapshot(_hot_stories())
    rt.recompute(hot, [])
    assert hot['tension'] > FOSSIL_TENSION, \
        f"conflict stories must raise tension above fossil {FOSSIL_TENSION}, got {hot['tension']}"
