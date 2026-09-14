"""Unit tests for the quake + fire tension-signal adapters (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import update_fire_events as fires
import update_quake_events as quake


def test_quake_drops_below_threshold():
    assert quake.score_quake({'mag': 4.9, 'place': 'Japan'}, [140.0, 35.0, 10.0]) is None


def test_quake_drops_missing_mag():
    assert quake.score_quake({'place': 'Japan'}, [140.0, 35.0, 10.0]) is None


def test_quake_big_shallow_populated_scores_high():
    ev = quake.score_quake(
        {'mag': 7.2, 'place': '20km off the coast of Japan', 'tsunami': 1,
         'felt': 500, 'sig': 700, 'url': 'https://example.com/x', 'code': 'q1'},
        [142.0, 38.0, 15.0])
    assert ev is not None
    assert ev['score'] >= 60 and ev['level'] in ('HIGH', 'CRITICAL')
    assert ev['kind'] == 'earthquake'


def test_quake_deep_remote_scores_lower():
    shallow = quake.score_quake({'mag': 6.0, 'place': 'Japan', 'code': 's'},
                                [140.0, 35.0, 10.0])
    deep = quake.score_quake({'mag': 6.0, 'place': 'Japan', 'code': 'd'},
                             [140.0, 35.0, 400.0])
    assert shallow is not None and deep is not None
    assert shallow['score'] > deep['score']


def test_quake_missing_place_never_invented():
    ev = quake.score_quake({'mag': 6.5, 'code': 'n'}, [-120.0, 40.0, 10.0])
    assert ev is not None
    assert 'pending review' in ev['title']


def test_quake_level_bands():
    assert quake.level_of(85) == 'CRITICAL'
    assert quake.level_of(65) == 'HIGH'
    assert quake.level_of(45) == 'ELEVATED'
    assert quake.level_of(30) == 'WATCH'


def test_fires_parse_guards_bad_coords():
    rows = fires.parse_rows(
        'latitude,longitude,confidence,frp\nbad,200,h,10\n35.0,-120.0,h,50\n')
    assert len(rows) == 1 and rows[0]['frp'] == 50.0


def test_fires_parse_missing_fields_absent():
    rows = fires.parse_rows('latitude,longitude\n35.0,-120.0\n')
    assert len(rows) == 1 and 'frp' not in rows[0] and 'conf' not in rows[0]


def test_fires_dense_cell_scores_and_caps():
    rows = [{'lat': 35.0 + i * 0.01, 'lon': -120.0, 'conf': 'high', 'frp': 20.0}
            for i in range(30)]
    cells = fires.cluster(rows)
    assert len(cells) == 1
    key, cell = next(iter(cells.items()))
    ev = fires.score_cell(key, cell)
    assert ev is not None and ev['score'] >= 40
    assert ev['hotspots'] == 30 and ev['kind'] == 'wildfire'


def test_fires_single_hotspot_dropped():
    cells = fires.cluster([{'lat': 35.0, 'lon': -120.0}])
    key, cell = next(iter(cells.items()))
    assert fires.score_cell(key, cell) is None


def test_fires_cache_fresh_logic(tmp_path, monkeypatch):
    import json
    from datetime import datetime, timezone
    monkeypatch.setattr(fires, 'OUT', tmp_path / 'fire_events.json')
    assert fires.cache_is_fresh() is False
    stamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    fires.OUT.write_text(json.dumps({'updatedAt': stamp, 'events': []}))
    assert fires.cache_is_fresh() is True
    fires.OUT.write_text(json.dumps({'updatedAt': '2020-01-01T00:00:00Z', 'events': []}))
    assert fires.cache_is_fresh() is False
