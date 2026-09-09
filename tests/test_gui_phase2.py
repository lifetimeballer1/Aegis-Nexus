"""GUI Phase 2 — Alerts & Timeline contracts.

Severity may only derive from pipeline-produced fields (conflict
`escalation`, event/history `confidence`); filters must show real counts;
undated/future timeline records must be excluded.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_alerts_derive_severity_from_pipeline_fields():
    text = (ROOT / 'js/modules/alerts.js').read_text(encoding='utf-8')
    assert 'export function renderAlerts' in text
    assert 'escalation' in text
    assert 'confidence' in text
    assert 'escapeHtml' in text
    assert 'Alert queue unavailable' in text
    assert 'lorem' not in text.lower()


def test_alerts_filter_counts_and_expansion_are_wired():
    text = (ROOT / 'js/modules/alerts.js').read_text(encoding='utf-8')
    assert 'data-alert-level' in text
    assert 'data-alert-toggle' in text
    assert 'alertsMore' in text
    assert 'No alerts at this severity' in text


def test_timeline_uses_dated_observations_and_periods():
    text = (ROOT / 'js/modules/timeline.js').read_text(encoding='utf-8')
    assert 'export function renderTimeline' in text
    assert 'observations' in text
    assert 'observedAt' in text
    assert 'data-tl-period' in text
    for label in ('24H', '7D', '30D', 'ALL'):
        assert label in text
    assert 'getTime() > now' in text or 'future' in text.lower()
    assert 'No signals in this period' in text
    assert 'escapeHtml' in text
    assert 'userPicked' in text, 'manual period choice must stick once made'
    assert 'Showing' in text, 'timeline must report shown/total counts honestly'


def test_phase2_shell_and_boot_wiring():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="section-alerts"' in html
    assert 'id="alertsBody"' in html
    assert 'id="section-timeline"' in html
    assert 'id="timelineBody"' in html
    assert 'data-nav="alerts"' in html
    assert 'data-nav="timeline"' in html
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/alerts.js' in app
    assert './modules/timeline.js' in app
    assert 'renderAlerts' in app
    assert 'renderTimeline' in app
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert './data/event_history.json' in config
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'eventHistory' in state
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'eventHistory' in fetch


def test_phase2_styles_and_pages_safety():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('gp-sev-critical', 'gp-sev-high', 'gp-sev-medium', 'gp-sev-low', 'gp-filter', 'gp-timeline', 'gp-alert'):
        assert token in css, f'stylesheet missing {token}'
    for name in ('js/modules/alerts.js', 'js/modules/timeline.js'):
        text = (ROOT / name).read_text(encoding='utf-8')
        assert 'href="/' not in text and "src=\"/" not in text
        assert '/Aegis-Nexus/' not in text


def test_timeline_custom_range_and_alert_ack_are_wired():
    tl = (ROOT / 'js/modules/timeline.js').read_text(encoding='utf-8')
    assert 'CUSTOM' in tl
    assert 'data-tl-apply' in tl
    assert 'data-tl-clear' in tl
    assert 'custom range' in tl
    assert 'after end date' in tl
    al = (ROOT / 'js/modules/alerts.js').read_text(encoding='utf-8')
    assert 'data-alert-ack' in al
    assert 'gp.alertAck.v1' in al
    assert 'acknowledged' in al.lower()
    assert 'this device' in al
