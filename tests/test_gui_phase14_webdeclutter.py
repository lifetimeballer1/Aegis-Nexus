"""Phase 14 intel-web declutter contracts (text-only, no browser).

Covers the 2026-09-12 fix for the mobile intel-web view: overlapping
center-cluster labels, labels clipped past the viewport edge, and
uncapped label text widths.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _js():
    return (ROOT / 'intelligence_web_v2.js').read_text(encoding='utf-8')

def _html():
    return (ROOT / 'intelligence-web.html').read_text(encoding='utf-8')

def test_collision_helpers_present():
    t = _js()
    for name in ('labelEstBox', 'labelBoxesOverlap', 'clampLabelBox', 'keptIds'):
        assert name in t, f'missing declutter helper {name}'

def test_sync_labels_resolves_overlaps():
    t = _js()
    assert 'kept.some' in t, 'no overlap rejection pass in syncLabels'

def test_labels_clamped_to_viewport():
    t = _js()
    assert 'window.innerWidth' in t and 'window.innerHeight' in t
    assert 'clampLabelBox' in t

def test_label_text_ellipsis_capped():
    t = _html()
    assert '.node-label .text' in t
    assert 'text-overflow:ellipsis' in t
    assert 'max-width:30ch' in t

def test_mobile_label_text_shorter():
    t = _html()
    assert 'max-width:20ch' in t, 'mobile label text cap missing'

def test_no_layout_reads_in_hot_loop():
    t = _js()
    assert 'no layout reads' in t.lower() or 'estimated' in t.lower()

def test_hidden_label_hint_present():
    t = _js()
    assert 'label-hidden-hint' in t
    assert 'hiddenLabelBadge' in t
    assert 'more labels' in t

def test_hint_tap_zooms_in():
    t = _js()
    assert 'cameraPosition' in t
    assert 'aria-live' in t
