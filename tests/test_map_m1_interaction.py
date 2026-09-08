"""Map M1 — interaction repair contracts.

Locks the three fixes behind the click/zoom failures (verified in a real
browser via pixel-hunt clicks + localhost hooks):
1. Canvas sizing: Leaflet-compat guard + size recovery when the below-fold
   section renders (zero-size canvas = invisible, unclickable markers).
2. Click race: marker clicks must halt Leaflet's internal target loop
   (_stopped) AND native bubble, or map.on('click',closeDetail) closes the
   panel in the same tick the marker opens it.
3. View yank: background re-renders must not refit bounds (only the first
   render and explicit Fit/Reset fit).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_canvas_css_guard_keeps_markers_paintable():
    css = (ROOT / 'css/map.css').read_text(encoding='utf-8')
    assert '#mapContainer canvas' in css
    assert 'max-width:none' in css.replace(' ', '')


def test_map_recovers_size_when_section_renders():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'ensureMapSize' in text
    assert 'invalidateSize' in text
    assert 'IntersectionObserver' in text
    assert 'setView(map.getCenter(),map.getZoom()' in text.replace(' ', '')


def test_marker_click_halts_both_propagation_layers():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert '_stopped' in text, 'Leaflet internal loop must be halted or map click closes the panel same-tick'
    assert 'stopPropagation' in text
    assert 'showDetail(p)' in text
    assert "map.on('click',closeDetail)" in text, 'background-click dismiss must be preserved'


def test_background_renders_preserve_user_view():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'renderMap._fitted' in text, 'auto-fit must run once, not on every render'
    assert 'fitAll(points)' in text


def test_localhost_browser_hooks_for_m5_verification():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    for hook in ('gp:test-open-map-detail', 'gp:test-click-marker', 'gp:test-map-debug'):
        assert hook in text, f'missing browser hook {hook}'
    assert "location.hostname" in text
