"""GUI Phase 1 — Command Center Dashboard contracts.

Every dashboard figure must come from canonical artifacts; these tests lock
the wiring (module exports, state keys, shell hooks, severity language,
Pages-safe relative paths) without running a browser.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_module_reads_canonical_state_and_exports_renderer():
    text = (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
    assert 'export function renderDashboard' in text
    assert 'getState()' in text
    for key in ('snapshot', 'liveArticles', 'sourceHealth', 'mapData', 'whatChanged'):
        assert key in text, f'dashboard never reads state.{key}'
    assert 'escapeHtml' in text
    assert 'Loading command overview' in text
    assert 'Nothing new this window' in text or 'No changes recorded' in text


def test_dashboard_binds_real_artifact_fields_not_placeholders():
    text = (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
    for field in ('marketData', 'priorityOrder', 'consecutiveFailures', 'tensionDelta'):
        assert field in text, f'dashboard never binds real field {field}'
    assert 'lorem' not in text.lower()
    assert 'Mock' not in text


def test_dashboard_uses_shared_severity_language():
    module = (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('sev-info', 'sev-watch', 'sev-critical', 'sev-healthy'):
        assert token in css, f'stylesheet missing {token}'
    assert 'sev-' in module, 'module never applies severity classes'
    for level in ("'info'", "'watch'", "'critical'", "'healthy'"):
        assert level in module, f'module never selects severity {level}'
    assert '--sev-info' in css and '--sev-watch' in css
    assert '--sev-critical' in css and '--sev-healthy' in css
    assert '@media' in css


def test_dashboard_shell_hooks_exist_in_index():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'css/dashboard.css' in html
    assert 'id="section-dashboard"' in html
    assert 'id="dashboardBody"' in html
    assert 'id="commandStatus"' in html
    assert 'data-nav="dashboard"' in html
    for target in ('#section-map', '#section-brain', '#section-intelweb', '#section-markets', '#section-status'):
        assert target in html, f'command bar missing anchor {target}'


def test_dashboard_is_wired_into_boot_and_data_layer():
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert "'dashboardBody'" in app or '"dashboardBody"' in app
    assert './modules/dashboard.js' in app
    assert "renderDashboard" in app
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert 'what_changed.json' in config
    assert './data/what_changed.json' in config
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'whatChanged' in fetch
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'whatChanged' in state


def test_dashboard_mobile_rules_keep_shell_usable():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    assert 'overflow-x:auto' in css, 'command tabs / bottom nav must scroll, not crush, on mobile'
    assert '.gp-bottom-nav .gp-nav-item' in css
    assert 'overflow-wrap:break-word' in css, 'headline text must wrap inside narrow panels'


def test_dashboard_has_no_absolute_pages_paths():
    for name in ('js/modules/dashboard.js', 'css/dashboard.css'):
        text = (ROOT / name).read_text(encoding='utf-8')
        assert 'href="/' not in text and "src=\"/" not in text
        assert '/Aegis-Nexus/' not in text
