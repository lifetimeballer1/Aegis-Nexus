"""Live-intake health contracts (2026-09-14 intake unpinch).

Incident: the canonical refresh rebuilt live_articles.json (fresh, ~2000 rows)
but nothing merged it into snapshot.stories — merge_live_news.py was orphaned
from refresh_pipeline.py, so snapshot stories stalled at Sept 5-6 while every
downstream reader (tension, map, alerts) starved. These tests FAIL if intake
goes dry silently again:

- wiring: merge_live_news.py must run in refresh_pipeline.py right after the
  live-intelligence gate, and the snapshot must carry the liveDatabase marker.
- functional: normalize_article keeps valid UTC timestamps and drops invalid
  ones (garbage dates must never top the story sort).
- live backstop: the collector export must be fresh and the snapshot must carry
  recently-published stories (fails on a Sept-5-style stall).
"""
import json
from datetime import datetime,timezone,timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc)


def _parse(value):
    try:
        dt = parsedate_to_datetime(str(value))
    except Exception:
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def test_pipeline_wires_live_news_merge():
    src = (ROOT / 'refresh_pipeline.py').read_text(encoding='utf-8')
    assert 'merge_live_news.py' in src, \
        'merge_live_news.py not wired into refresh_pipeline.py — snapshot stories will rot again'
    assert 'liveDatabase' in src, \
        'pipeline does not verify the live-database merge marker on snapshot.json'
    # The merge must run before downstream consumers (health, canonical layer,
    # map points, event exports) so they read fresh stories.
    assert src.index('merge_live_news.py') < src.index('build_canonical_intelligence_v3.py'), \
        'live merge must precede the canonical-intelligence build'


def test_normalize_article_keeps_valid_drops_invalid():
    import merge_live_news as merge
    good = merge.normalize_article({'url': 'https://example.test/a', 'title': 'T',
                                    'published_date': NOW.isoformat(), 'source': 'Test'})
    assert good and good['url'] == 'https://example.test/a'
    assert _parse(good['published_date']) is not None
    assert merge.normalize_article({'url': 'https://example.test/b', 'title': 'T',
                                    'published_date': 'not a date', 'source': 'Test'}) is None
    assert merge.normalize_article({'title': 'No URL here', 'published_date': NOW.isoformat()}) is None


def test_live_export_is_fresh():
    live = json.loads((ROOT / 'data' / 'live_articles.json').read_text(encoding='utf-8'))
    articles = live.get('articles', [])
    assert len(articles) >= 100, f'live export suspiciously small: {len(articles)}'
    newest = max((_parse(a.get('published_date') or a.get('publishedDate') or a.get('time') or '')
                  for a in articles), default=None)
    assert newest is not None, 'no parseable timestamps in live export'
    age_h = (NOW - newest).total_seconds() / 3600
    assert -1 < age_h < 6, f'live intake dry: newest article {age_h:.1f}h old'


def test_snapshot_carries_recent_stories():
    snap = json.loads((ROOT / 'data' / 'snapshot.json').read_text(encoding='utf-8'))
    stories = snap.get('stories', [])
    assert len(stories) >= 10, f'snapshot stories depleted: {len(stories)}'
    cutoff = NOW - timedelta(hours=72)
    recent = [s for s in stories
              if (_parse(s.get('time') or s.get('published_date') or '') or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    assert len(recent) >= 3, \
        f'snapshot intake stall: only {len(recent)} stories newer than 72h of {len(stories)} — merge unwired?'
