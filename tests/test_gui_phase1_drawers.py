"""GUI Phase 1 tranche 2 — shared gp-drawer pattern for phone rails.

Concept 05/06 desktop layouts pair a center feed with side rails; on phones
those rails must become slide-in drawers (never stacked content-blocking
cards, never a desktop layout change). Locks the shared pattern
(css/drawer.css + js/core/drawer.js + #gpDrawerScrim) and its wiring into
every tab the fidelity audit flagged: map signal panel (5a), timeline
reading pane, briefings development detail (4b), sources drill-down (7a).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def test_drawer_stylesheet_exists_and_linked():
    assert (ROOT / 'css/drawer.css').exists(), 'missing css/drawer.css'
    html = _read('index.html')
    assert 'href="css/drawer.css"' in html, 'drawer.css not linked in index.html'


def test_drawer_phone_breakpoint_and_desktop_untouched():
    css = _read('css/drawer.css')
    assert '.gp-drawer' in css
    assert '.gp-drawer.open' in css
    assert '#gpDrawerScrim' in css
    assert '1023' in css, 'no sub-1024px phone drawer query'
    assert '1024' in css, 'no >=1024px desktop rule (desktop must stay in place)'
    assert 'prefers-reduced-motion' in css


def test_drawer_controller_exports():
    js = _read('js/core/drawer.js')
    for name in ('openDrawer', 'closeDrawer', 'closeAllDrawers', 'initDrawers', 'isPhoneDrawer'):
        assert name in js, 'drawer.js lacks %s' % name
    assert 'Escape' in js, 'no Esc-to-close handling'
    assert 'data-drawer-close' in js, 'no delegated close-button handling'


def test_drawer_scrim_present():
    assert 'id="gpDrawerScrim"' in _read('index.html')


def test_map_panel_is_drawer_without_inline_display():
    html = _read('index.html')
    assert 'id="mapSidePanel" class="gp-card gp-drawer"' in html
    js = _read('js/modules/map.js')
    assert 'openDrawer' in js and 'closeDrawer' in js
    assert "panel.style.display" not in js, 'map panel still uses inline display styling'
    assert 'data-drawer-close' in js


def test_timeline_reading_pane_is_drawer():
    js = _read('js/modules/timeline.js')
    assert 'tlReadingPane' in js
    assert 'gp-drawer' in js
    assert 'openDrawer' in js


def test_briefings_development_detail_drawer():
    js = _read('js/modules/briefings.js')
    assert 'briefDrawer' in js
    assert 'data-brief-dev' in js
    assert 'openDrawer' in js


def test_sources_drilldown_drawer():
    js = _read('js/modules/status.js')
    assert 'srcDrawer' in js
    assert 'data-src-drill' in js
    assert 'openDrawer' in js
