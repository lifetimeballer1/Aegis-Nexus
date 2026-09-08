"""GUI Phase 3 — Geospatial Operations Map contracts.

The operations workspace must read the canonical validated browser feed
(data/map_points.json with markers/updatedAt/count) through core state;
layer filters must show real counts from the same pipeline that drives
Leaflet markers; search/filter must stay honest with empty states.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_map_ops_reads_canonical_points_feed():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'export function renderMapOps' in text
    assert 'export function renderMap' in text
    assert 'mapPoints' in text, 'ops never reads canonical state.mapPoints'
    assert 'markers' in text
    assert 'updatedAt' in text
    assert 'escapeHtml' in text
    assert 'Loading map operations' in text
    assert 'Map signals unavailable' in text
    assert 'lorem' not in text.lower()


def test_map_ops_filters_counts_search_and_empty_states():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'data-map-ops-filter' in text
    assert 'mapOpsSearch' in text
    assert 'mapOpsBody' in text
    assert 'No signals match' in text
    assert 'Showing' in text, 'ops must report shown/total counts honestly'
    for layer in ('conflicts', 'hazards', 'strategic', 'cartel', 'osint'):
        assert layer in text, f'ops never handles layer {layer}'
    assert 'sev-' in text, 'ops must use shared severity language'


def test_phase3_shell_and_boot_wiring():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="section-map"' in html
    assert 'id="mapOpsBody"' in html
    assert 'id="mapContainer"' in html
    assert 'id="mapUpdated"' in html
    assert 'data-nav="map"' in html
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/map.js' in app
    assert 'renderMap' in app
    assert 'renderMapOps' in app
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert './data/map_points.json' in config
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'mapPoints' in state
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'mapPoints' in fetch


def test_phase3_styles_and_pages_safety():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('gp-map-ops-bar', 'gp-map-ops-list', 'gp-map-op-row', 'gp-map-op-dot'):
        assert token in css, f'stylesheet missing {token}'
    assert 'sev-critical' in css and 'sev-watch' in css
    assert '@media' in css
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'href="/' not in text and 'src="/' not in text
    assert '/Aegis-Nexus/' not in text
