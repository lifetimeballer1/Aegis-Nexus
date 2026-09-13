"""GUI Phase 9 — responsive/mobile hardening contracts (final GUI phase).

Locks the shared mobile invariants across all workspaces: safe-area
viewport, scrollable nav (10 bottom items, 9 command tabs), wrapping
section headers with truncating stamps, 36px touch targets, no-crush
section layout, and preserved deferred loading for expensive WebGL.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_viewport_and_safe_area_shell():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'width=device-width' in html
    assert 'viewport-fit=cover' in html
    layout = (ROOT / 'css/layout.css').read_text(encoding='utf-8')
    assert 'safe-bottom' in layout or 'safe-area' in layout


def test_nav_scales_to_all_workspace_items():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    layout = (ROOT / 'css/layout.css').read_text(encoding='utf-8')
    assert '.gp-bottom-nav{overflow-x:auto' in css.replace(' ', '') or '.gp-bottom-nav' in css and 'overflow-x:auto' in css
    assert 'min-height:48px' in layout, 'bottom-nav touch targets must stay 48px'
    assert '.gp-command-tabs' in css and 'overflow-x:auto' in css
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert html.count('class="gp-nav-item"') >= 18, 'both nav bars must carry all workspaces'


def test_section_headers_wrap_and_truncate_on_mobile():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    assert '.gp-section-header{flex-wrap:wrap' in css.replace(' ', '')
    assert 'text-overflow:ellipsis' in css


def test_touch_targets_meet_minimum():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    assert '.gp-filter{min-height:36px' in css.replace(' ', '')
    assert '.gp-btn{min-height:36px' in css.replace(' ', '')


def test_sections_cannot_crush_content():
    layout = (ROOT / 'css/layout.css').read_text(encoding='utf-8')
    assert '.gp-section' in layout and 'min-width:0' in layout
    assert '.gp-section-body' in layout and 'overflow-wrap' in layout or 'min-width:0' in layout
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    assert 'overflow-wrap:break-word' in css


def test_expensive_webgl_stays_deferred():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'loading="lazy"' in html
    perf = (ROOT / 'global_pulse_performance.js').read_text(encoding='utf-8')
    assert 'IntersectionObserver' in perf
    assert 'prefers-reduced-motion' in perf or 'reduced-motion' in perf
    assert 'contentVisibility' in perf
    web = (ROOT / 'js/modules/intelligence-web.js').read_text(encoding='utf-8')
    assert 'gpWebLoad3d' in web, 'dashboard 3D must stay opt-in'
def test_map_ops_bar_no_crush():
    css = (ROOT / "css/dashboard.css").read_text(encoding="utf-8")
    flat = css.replace(" ", "")
    assert ".gp-map-ops-bar{flex-wrap:nowrap" in flat
    assert "overflow-x:auto" in css
