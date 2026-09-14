#!/usr/bin/env python3
"""Fetch NASA FIRMS active fires, cluster them, publish scored tension events.

Requires a free FIRMS MAP_KEY in env FIRMS_MAP_KEY (mint one at
https://firms.modaps.eosdis.nasa.gov/api/area/). Without the key the adapter
exits 0 and serves the stale file — it never blocks the pipeline.

Output: data/fire_events.json — scored events the tension index can consume
(score 0-100, level, evidence URLs). Raw per-hotspot CSV rows are aggregated
into 1-degree cells and only scored cells are kept.

Resilience: 30-min TTL cache (skip fetch when the file is fresh),
validate-then-swap, serve-stale on failure, per-source kill switch via
AEGIS_FIRES_DISABLED=1. No invented data: missing fields = absent.
"""
from __future__ import annotations
import csv, io, json, os, tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
OUT = DATA / 'fire_events.json'
UA = 'Mozilla/5.0 (compatible; GlobalPulse/14.0)'
SOURCE = 'VIIRS_SNPP_NRT'
CACHE_TTL_SECONDS = 30 * 60
MAX_CELLS = 25       # publish at most the top-N scored cells
MIN_SCORE = 30


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


def cache_is_fresh() -> bool:
    if not OUT.is_file():
        return False
    try:
        stamp = (json.loads(OUT.read_text(encoding='utf-8')) or {}).get('updatedAt')
        if not stamp:
            return False
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))).total_seconds()
        return 0 <= age < CACHE_TTL_SECONDS
    except Exception:
        return False


def fetch_csv(map_key: str, timeout: int = 25) -> str:
    url = ('https://firms.modaps.eosdis.nasa.gov/api/area/csv/'
           '%s/%s/%s/world/1' % ('VERSION_PLACEHOLDER', map_key, SOURCE))
    # NOTE: API version segment is pinned below in API_VERSION.
    url = url.replace('VERSION_PLACEHOLDER', API_VERSION)
    req = Request(url, headers={'User-Agent': UA, 'Accept': 'text/csv'})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')


API_VERSION = '2.0'


def parse_rows(text: str) -> list:
    """Parse FIRMS CSV into hotspot dicts. Guards every field; missing=absent."""
    rows = []
    try:
        reader = csv.DictReader(io.StringIO(text))
    except Exception:
        return []
    for row in reader:
        try:
            lat = float(row.get('latitude'))
            lon = float(row.get('longitude'))
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        hot = {'lat': lat, 'lon': lon}
        conf = str(row.get('confidence') or '').strip().lower()
        if conf in ('h', 'high', 'n', 'nominal'):
            hot['conf'] = 'high' if conf in ('h', 'high') else 'nominal'
        try:
            frp = float(row.get('frp'))
            if frp >= 0:
                hot['frp'] = frp
        except (TypeError, ValueError):
            pass
        for key in ('acq_date', 'acq_time', 'satellite', 'daynight'):
            val = (row.get(key) or '').strip()
            if val:
                hot[key] = val
        rows.append(hot)
    return rows


def cluster(rows: list) -> dict:
    """Aggregate hotspots into 1-degree cells. Returns cell-key -> stats."""
    cells = defaultdict(lambda: {'count': 0, 'frp': 0.0, 'high': 0,
                                 'lats': [], 'lons': [], 'dates': set()})
    for h in rows:
        key = (int(h['lat']), int(h['lon']))
        c = cells[key]
        c['count'] += 1
        if 'frp' in h:
            c['frp'] += h['frp']
        if h.get('conf') == 'high':
            c['high'] += 1
        c['lats'].append(h['lat'])
        c['lons'].append(h['lon'])
        if h.get('acq_date'):
            c['dates'].add(h['acq_date'])
    return cells


def score_cell(key: tuple, c: dict) -> dict | None:
    """Score one fire cell. Returns scored event or None (drop)."""
    # Base on hotspot density: 1 -> 12, 5 -> 32, 10 -> 44, 25 -> 62, 50+ -> 78.
    import math
    score = 12.0 + 22.0 * math.log10(1 + c['count'])
    if c['frp'] > 0:
        # FRP energy bonus, capped: 100 MW -> +8, 1000 MW -> +16.
        score += min(16.0, 8.0 * math.log10(1 + c['frp'] / 10.0))
    if c['count'] > 0 and c['high'] / c['count'] >= 0.5:
        score += 8  # majority high-confidence detections
    score = max(0.0, min(100.0, round(score, 1)))
    if score < MIN_SCORE:
        return None
    n = max(1, len(c['lats']))
    event = {
        'id': 'firms-%d-%d' % (key[0], key[1]),
        'kind': 'wildfire',
        'title': 'Active fire cluster — %d hotspots near %.1f, %.1f'
                 % (c['count'], sum(c['lats']) / n, sum(c['lons']) / n),
        'hotspots': c['count'],
        'lat': round(sum(c['lats']) / n, 3),
        'lon': round(sum(c['lons']) / n, 3),
        'score': score,
        'level': level_of(score),
        'evidence': [{'source': 'NASA FIRMS %s' % SOURCE,
                      'url': 'https://firms.modaps.eosdis.nasa.gov/map/'}],
    }
    if c['frp'] > 0:
        event['frpMW'] = round(c['frp'], 1)
    if c['dates']:
        event['observedDates'] = sorted(c['dates'])[-3:]
    return event


def build(map_key: str, timeout: int = 25) -> dict:
    rows = parse_rows(fetch_csv(map_key, timeout))
    events = []
    for key, c in cluster(rows).items():
        scored = score_cell(key, c)
        if scored is not None:
            events.append(scored)
    events.sort(key=lambda e: e['score'], reverse=True)
    events = events[:MAX_CELLS]
    return {
        'updatedAt': now_iso(),
        'source': 'NASA FIRMS %s (keyed, free MAP_KEY)' % SOURCE,
        'scoring': {'minScore': MIN_SCORE, 'maxCells': MAX_CELLS,
                    'rules': 'log-density base; FRP energy bonus; high-confidence '
                             'majority boost; missing=absent'},
        'hotspotsSeen': len(rows),
        'eventCount': len(events),
        'events': events,
    }


def main() -> None:
    if os.environ.get('AEGIS_FIRES_DISABLED') == '1':
        print('FIRES: kill switch set (AEGIS_FIRES_DISABLED=1); serving stale file.')
        return
    map_key = os.environ.get('FIRMS_MAP_KEY', '').strip()
    if not map_key:
        print('FIRES: no FIRMS_MAP_KEY in env — mint a free key at '
              'https://firms.modaps.eosdis.nasa.gov/api/area/ ; serving stale file.')
        return
    if cache_is_fresh():
        print('FIRES: cache fresh (<30 min); skipping fetch.')
        return
    try:
        doc = build(map_key)
    except Exception as exc:
        if OUT.is_file():
            print('WARNING: FIRMS fetch failed (%s); serving stale %s.' % (exc, OUT.name))
            return
        raise SystemExit('FIRES REFRESH BLOCKED: fetch failed and no stale file: %s' % exc)
    if not isinstance(doc.get('events'), list):
        raise SystemExit('FIRES REFRESH BLOCKED: built document has no events list')
    DATA.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=DATA, delete=False,
                                     encoding='utf-8') as tmp:
        json.dump(doc, tmp, ensure_ascii=False, indent=2)
        tmp.write('\n')
        tmp_path = tmp.name
    json.loads(Path(tmp_path).read_text(encoding='utf-8'))  # re-parse gate
    Path(tmp_path).rename(OUT)
    print('FIRES: published %d scored cells (%d hotspots) -> %s'
          % (doc['eventCount'], doc['hotspotsSeen'], OUT.name))


if __name__ == '__main__':
    main()
