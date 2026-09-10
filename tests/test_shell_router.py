"""S1-S14 — app shell router contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_router_module_contract():
    text = (ROOT / 'js/core/router.js').read_text(encoding='utf-8')
    for token in ('setupRouter', 'showView', 'onActivate', 'currentView', 'hashchange', 'popstate', 'data-more-toggle', 'gpMoreSheet'):
        assert token in text, f'router missing {token}'
    assert "overview: 'dashboard'" in text, 'overview must fold into the dashboard view'
    assert "'#section-'" in text or '#section-' in text


def test_app_boots_through_router_with_lazy_views():
    text = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert "from './core/router.js'" in text
    assert 'setupRouter()' in text
    assert 'VIEW_RENDER' in text
    assert 'renderView(currentView()' in text, 'state changes must re-render only the active view'
    assert 'setupNav' not in text, 'legacy scroll observer navigation must be gone'
    assert 'initMap' in text and "'intelweb'" in text, 'view activation hooks must exist'


def test_index_shell_markup():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'data-more-toggle' in html
    assert 'id="gpMoreSheet"' in html
    assert html.count('class="gp-nav-item"') >= 18, 'navigation contract requires >=18 gp-nav-item anchors'
    for section in ('dashboard', 'map', 'brain', 'alerts', 'intelweb', 'breaking', 'timeline', 'briefings', 'search', 'status', 'settings', 'markets', 'conflicts', 'overview'):
        assert f'data-nav="{section}"' in html, f'missing nav for {section}'
    assert 'News \u00b7 Latest Reporting' in html, 'Breaking view must present as News'
    assert 'class="gp-bottom-nav"' in html and 'loading="lazy"' in html


def test_home_is_stories_first():
    text = (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
    assert 'What matters now' in text
    assert 'storiesPanel' in text
    assert 'dashSearch' not in text, 'headline feed moved to the News view'


def test_smoke_routes_before_asserting():
    text = (ROOT / 'tests/dashboard_smoke.py').read_text(encoding='utf-8')
    assert 'def go_view' in text
    for view in ('map', 'brain', 'intelweb', 'dashboard'):
        assert f"go_view(page, '{view}')" in text or f'go_view(page, "{view}")' in text, f'smoke must route {view}'
