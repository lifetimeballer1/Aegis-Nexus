#!/usr/bin/env python3
"""Fetch USGS all-day earthquakes, score them, publish scored tension events.

Keyless public-domain feed. Output: data/quake_events.json — scored events
the tension index can consume (score 0-100, level, evidence URLs).
Only scored events are kept; the raw 100-300KB feed is never stored.

Resilience: validate-then-swap (write tmp, validate, rename), serve-stale on
fetch failure (keep last good file, exit 0), per-source kill switch via
AEGIS_QUAKE_DISABLED=1. No invented data: missing fields = absent, never
zero-filled or defaulted into a score boost.
"""
from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
OUT = DATA / 'quake_events.json'
FEED = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson'
UA = 'Mozilla/5.0 (compatible; GlobalPulse/14.0)'
MIN_MAG = 5.5          # below this: not scored, dropped
MIN_SCORE = 30         # below this: not published

# Populated-region heuristic: substrings matched against USGS `place`.
# Absence of a match = no boost (never a penalty, never invented).
POPULATED_HINTS = {
    'japan', 'china', 'taiwan', 'philippines', 'indonesia', 'india', 'nepal',
    'pakistan', 'bangladesh', 'iran', 'turkey', 'turkiye', 'greece', 'italy',
    'mexico', 'chile', 'peru', 'colombia', 'ecuador', 'venezuela', 'haiti',
    'california', 'alaska', 'washington', 'oregon', 'nevada', 'utah',
    'papua new guinea', 'new zealand', 'vanuatu', 'tonga', 'fiji', 'samoa',
    'solomon', 'afghanistan', 'myanmar', 'thailand', 'vietnam', 'malaysia',
    'korea', 'russia', 'kamchatka', 'kuril', 'sakhalin', 'java', 'sumatra',
    'sulawesi', 'mindanao', 'luzon', 'honshu', 'hokkaido', 'kyushu',
    'istanbul', 'athens', 'rome', 'lima', 'santiago', 'bogota', 'quito',
    'kathmandu', 'jakarta', 'manila', 'taipei', 'tokyo', 'osaka', 'seoul',
    'beijing', 'delhi', 'tehran', 'mexico city', 'los angeles', 'san francisco',
    'seattle', 'portland', 'anchorage', 'honolulu', 'hawaii',
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def level_of(score: float) -> str:
    if score >= 80:
        return 'CRITICAL'
    if score >= 60:
        return 'HIGH'
    if score >= 40:
        return 'ELEVATED'
    return 'WATCH'


def score_quake(props: dict, coords: list) -> dict | None:
    """Score one USGS feature. Returns scored event dict or None (drop)."""
    if not isinstance(props, dict):
        return None
    mag = props.get('mag')
    if mag is None:
        return None  # missing magnitude = absent, never zero-filled
    try:
        mag = float(mag)
    except (TypeError, ValueError):
        return None
    if mag < MIN_MAG:
        return None

    depth = None
    if isinstance(coords, list) and len(coords) >= 3 and coords[2] is not None:
        try:
            depth = float(coords[2])
        except (TypeError, ValueError):
            depth = None

    # Base: M5.5 -> 30, M6.0 -> 40, M7.0 -> 65, M8.0 -> 90, M9.0 -> 100.
    score = 30.0 + (mag - 5.5) * 20.0
    # Shallow quakes do more damage: depth < 70km boosts, deep quakes reduce.
    if depth is not None:
        if depth < 30:
            score += 10
        elif depth < 70:
            score += 5
        elif depth > 300:
            score -= 10
        elif depth > 150:
            score -= 5
    # Populated-region heuristic from `place` (real USGS string only).
    place = str(props.get('place') or '')
    if place and any(h in place.lower() for h in POPULATED_HINTS):
        score += 10
    # Real USGS impact telemetry only — each guarded, missing = no boost.
    try:
        felt = props.get('felt')
        if felt is not None and int(felt) >= 100:
            score += 5
    except (TypeError, ValueError):
        pass
    if props.get('tsunami') == 1:
        score += 10
    try:
        sig = props.get('sig')
        if sig is not None and int(sig) >= 600:
            score += 5
    except (TypeError, ValueError):
        pass

    score = max(0.0, min(100.0, round(score, 1)))
    if score < MIN_SCORE:
        return None

    lon = coords[0] if isinstance(coords, list) and len(coords) > 0 else None
    lat = coords[1] if isinstance(coords, list) and len(coords) > 1 else None
    event = {
        'id': str(props.get('code') or props.get('ids') or props.get('id') or ''),
        'kind': 'earthquake',
        'title': 'M%.1f earthquake — %s' % (mag, place or 'location pending review'),
        'magnitude': mag,
        'lat': lat,
        'lon': lon,
        'score': score,
        'level': level_of(score),
        'time': props.get('time'),
        'evidence': [{'source': 'USGS Earthquake Hazards Program',
                      'url': props.get('url') or props.get('detail')}],
    }
    # Strip nulls: missing = absent.
    return {k: v for k, v in event.items() if v is not None}


def fetch_feed(timeout: int = 20) -> dict:
    req = Request(FEED, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def build(timeout: int = 20) -> dict:
    feed = fetch_feed(timeout)
    events = []
    for feat in (feed.get('features') or []):
        if not isinstance(feat, dict):
            continue
        geom = feat.get('geometry') or {}
        scored = score_quake(feat.get('properties') or {}, geom.get('coordinates') or [])
        if scored is not None:
            events.append(scored)
    events.sort(key=lambda e: e['score'], reverse=True)
    return {
        'updatedAt': now_iso(),
        'source': 'USGS Earthquake Hazards Program (public domain, keyless)',
        'feed': FEED,
        'scoring': {'minMagnitude': MIN_MAG, 'minScore': MIN_SCORE,
                    'rules': 'M>=5.5 base; shallow-depth boost; populated-place boost; '
                             'felt/tsunami/significance telemetry boost; missing=absent'},
        'eventCount': len(events),
        'events': events,
    }


def main() -> None:
    if os.environ.get('AEGIS_QUAKE_DISABLED') == '1':
        print('QUAKE: kill switch set (AEGIS_QUAKE_DISABLED=1); serving stale file.')
        return
    try:
        doc = build()
    except Exception as exc:
        if OUT.is_file():
            print('WARNING: USGS fetch failed (%s); serving stale %s.' % (exc, OUT.name))
            return
        raise SystemExit('QUAKE REFRESH BLOCKED: fetch failed and no stale file: %s' % exc)
    # Validate-then-swap.
    if not isinstance(doc.get('events'), list):
        raise SystemExit('QUAKE REFRESH BLOCKED: built document has no events list')
    DATA.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=DATA, delete=False,
                                     encoding='utf-8') as tmp:
        json.dump(doc, tmp, ensure_ascii=False, indent=2)
        tmp.write('\n')
        tmp_path = tmp.name
    json.loads(Path(tmp_path).read_text(encoding='utf-8'))  # re-parse gate
    Path(tmp_path).rename(OUT)
    print('QUAKE: published %d scored events -> %s' % (doc['eventCount'], OUT.name))


if __name__ == '__main__':
    main()
