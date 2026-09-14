"""Map-window fallback regression (2026-09-14 fix-map-windows).

Symptom: command mini-map chips 24H/7D/30D showed "0 of 80 signals - No dated
signals in this window". Diagnosis: the reader was innocent - eventTime() reads
lastSeen, present on 80/80 rows and all parseable; the rows were simply stale
(newest lastSeen ~8d old; live intake dry - breaking_news.json 0 articles since
GDELT 429s on 2026-09-10). Fix: the reader falls back to latest-available with
an honest note instead of a dead blank. These tests pin that contract:

- reader field priority covers the export shape (guards future shape drift)
- signals stamped with current dates match their windows
- every live_events.json row carries a parseable reader date
- the stale-window fallback helper exists and its note is honest
"""
import json
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _js():
    return (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')


def _fields():
    m = re.search(r'export function eventTime\(e\) \{ return ([^;]+); \}', _js())
    assert m, 'eventTime reader missing from dashboard.js'
    fields = re.findall(r'e\?\.\s*(\w+)', m.group(1))
    assert fields, 'no reader fields parsed'
    return fields


def _event_time(e, fields):
    for f in fields:
        v = e.get(f)
        if v:
            return v
    return None


def _parse(t):
    s = str(t).strip()
    try:
        if s and s[0].isdigit() and 'T' in s:
            return datetime.fromisoformat(s.replace('Z', '+00:00'))
        return parsedate_to_datetime(s)
    except Exception:
        return None


def _in_window(e, period, now, fields):
    """Python mirror of dashboard.js inMapWindow (same field priority, same cutoffs)."""
    t = _event_time(e, fields)
    if not t:
        return False
    ms = _parse(t)
    if ms is None:
        return False
    if ms.tzinfo is None:
        ms = ms.replace(tzinfo=timezone.utc)
    age_h = (now - ms).total_seconds() / 3600
    if period == '7D':
        return age_h <= 7 * 24
    if period == '30D':
        return age_h <= 30 * 24
    return age_h <= 24


def _sig(**kw):
    base = {'id': 't', 'title': 't', 'reportCount': 1}
    base.update(kw)
    return base


def test_reader_field_priority_covers_export_shape():
    fields = _fields()
    assert fields[0] == 'lastSeen', f'first reader field changed: {fields}'
    for f in ('lastSeen', 'firstSeen', 'published', 'publishedAt', 'time', 'date', 'updatedAt'):
        assert f in fields, f'reader no longer covers export field {f}'


def test_current_dated_signals_match_their_windows():
    fields = _fields()
    now = datetime.now(timezone.utc)
    iso = lambda dt: dt.isoformat()
    s24 = _sig(lastSeen=iso(now - timedelta(hours=2)))
    s7 = _sig(lastSeen=iso(now - timedelta(days=3)))
    s30 = _sig(lastSeen=iso(now - timedelta(days=20)))
    sold = _sig(lastSeen=iso(now - timedelta(days=60)))
    assert _in_window(s24, '24H', now, fields)
    assert _in_window(s24, '7D', now, fields)
    assert _in_window(s7, '7D', now, fields) and not _in_window(s7, '24H', now, fields)
    assert _in_window(s30, '30D', now, fields) and not _in_window(s30, '7D', now, fields)
    assert not any(_in_window(sold, p, now, fields) for p in ('24H', '7D', '30D'))


def test_export_rows_all_carry_parseable_reader_dates():
    fields = _fields()
    d = json.loads((ROOT / 'data/live_events.json').read_text(encoding='utf-8'))
    ev = d['events']
    assert len(ev) > 0, 'live_events.json has no events'
    bad = [e.get('id') for e in ev if _parse(_event_time(e, fields) or '') is None]
    assert not bad, f'{len(bad)} rows lack a parseable reader date, e.g. {bad[:3]}'


def test_stale_window_falls_back_to_latest_available():
    t = _js()
    assert 'export function resolveMapWindow' in t
    assert 'export function fallbackNote' in t
    assert 'shown: dated' in t, 'fallback must show dated signals when window is empty'
    assert 'latest available' in t.lower()
    assert 'resolveMapWindow(events, mapPeriod)' in t
    assert 'mapWin.fallback' in t
    # no dead-end advice on the widest window: the old copy told users on 30D
    # to "try 7D/30D"
    assert 'try 7D/30D' not in t


def test_stale_only_fixtures_still_resolve_to_latest():
    """Behavioural pin: all-old fixtures match no window but resolve non-empty."""
    fields = _fields()
    now = datetime.now(timezone.utc)
    evs = [_sig(id=str(i), lastSeen=(now - timedelta(days=60 + i)).isoformat()) for i in range(5)]
    assert not any(_in_window(e, '24H', now, fields) for e in evs)
    assert not any(_in_window(e, '7D', now, fields) for e in evs)
    dated = sorted(
        (e for e in evs if _event_time(e, fields) and _parse(_event_time(e, fields)) is not None),
        key=lambda e: _parse(_event_time(e, fields)),
    )
    assert len(dated) == 5, 'fallback set must be non-empty: latest available shown'
    newest_age_h = (now - _parse(_event_time(dated[-1], fields))).total_seconds() / 3600
    assert newest_age_h > 30 * 24, 'fixture should be older than every window'
