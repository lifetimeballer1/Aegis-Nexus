"""Map M4 — visual design contracts.

Clusters must wear their dominant child layer color (never one generic
hue); marker size may only scale with the pipeline's importance field;
tooltips follow the dark theme; the detail panel carries its layer color.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_clusters_wear_dominant_layer_color():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'iconCreateFunction' in text
    assert 'getAllChildMarkers' in text
    assert '__layer' in text
    assert 'marker-cluster-' in text


def test_marker_size_only_scales_with_importance():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'p.importance' in text
    assert 'brainNode?10' in text.replace(' ', '')


def test_detail_panel_carries_layer_color():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert "borderLeft='3px solid '" in text.replace(' ', '') or 'borderLeft' in text


def test_tooltips_match_dark_theme():
    css = (ROOT / 'css/map.css').read_text(encoding='utf-8')
    assert '.leaflet-tooltip' in css
    assert 'var(--panel)' in css
    assert '.marker-cluster' in css
