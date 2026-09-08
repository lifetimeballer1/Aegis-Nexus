"""Map M2 — rendering + clustering performance contracts.

Background state updates must not rebuild thousands of markers when the
underlying feeds, filters, and layers are unchanged (flicker/CPU); the
marker cap must be explicit and honest when hit; clustering must stay
chunked with declustering above the threshold.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_render_skips_rebuild_when_fingerprint_unchanged():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'renderFingerprint' in text
    assert 'renderMap._fp' in text
    for key in ('updatedAt', 'filter', 'query', 'enabled', 'showBrainLinks'):
        assert key in text, f'fingerprint never covers {key}'


def test_marker_cap_is_named_and_honest():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'MAP_RENDER_CAP' in text
    assert 'capped' in text
    assert 'of' in text and 'cap' in text.lower()


def test_clustering_stays_chunked_with_declustering():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'markerClusterGroup' in text
    assert 'chunkedLoading' in text
    assert 'disableClusteringAtZoom' in text
    assert 'spiderfyOnMaxZoom' in text
    assert 'preferCanvas' in text
