"""Map M3 — interface coherence contracts.

The toolbar, layer panel, header filters, and ops panel share one filter
state: layer toggles, reset, and both search boxes must refresh markers
AND the ops workspace together. Dead UI stays out; controls expose
accessible names; header filters double as a color legend.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_layer_panel_and_search_stay_synced_with_ops():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'renderMap();renderMapOps()' in text.replace(' ', '').replace('\n', '') or text.count('renderMapOps()') >= 5, \
        'layer toggles, reset, and searches must refresh markers and ops together'
    assert 'aria-label="Search map signals"' in text or 'aria-label="Filter map signals"' in text
    assert 'aria-expanded' in text


def test_header_filters_carry_legend_dots():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    for color in ('#ff405f', '#ffd34d', '#4d9aff', '#ff8a35'):
        assert color in html, f'header legend missing dot {color}'
    assert 'gp-map-layer-dot' in html


def test_dead_filter_panel_is_gone():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'mapFilterPanel' not in html, 'dead hidden filter panel must go'
    assert 'data-map-filter' not in html
    assert 'gp-map-filter-panel' not in html
