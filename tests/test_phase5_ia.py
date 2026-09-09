"""Phase 5 — global IA contracts.

Ctrl+K must focus universal search; saved views must capture/apply
cross-module filters device-locally; settings must expose refresh prefs,
device-data clearing, and honest build facts. No new absolute paths.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_search_shortcut_and_views_wiring():
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert 'universalSearch' in app
    assert "'k'" in app or '"k"' in app
    assert 'gp:prefs-changed' in app
    views = (ROOT / 'js/modules/views.js').read_text(encoding='utf-8')
    assert 'export function renderViews' in views
    assert 'gp.savedViews.v1' in views
    assert 'data-view-apply' in views and 'data-view-del' in views and 'data-view-save' in views
    assert 'setAlertLevel' in views and 'setTimelineView' in views and 'setBriefCategory' in views
    for name in ('js/modules/alerts.js', 'js/modules/timeline.js', 'js/modules/briefings.js'):
        text = (ROOT / name).read_text(encoding='utf-8')
        assert 'href="/' not in text and 'src="/' not in text
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="viewsBody"' in html
    assert 'id="section-settings"' in html
    assert 'id="settingsBody"' in html
    assert 'data-nav="settings"' in html


def test_settings_are_device_local_and_honest():
    text = (ROOT / 'js/modules/settings.js').read_text(encoding='utf-8')
    assert 'export function renderSettings' in text
    assert 'gp.prefs.v1' in text
    assert 'data-store-clear' in text
    assert 'never uploaded' in text
    assert 'confirm(' in text
    assert 'lorem' not in text.lower()
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/settings.js' in app
    assert './modules/views.js' in app
    assert 'renderSettings' in app
    assert 'renderViews' in app
