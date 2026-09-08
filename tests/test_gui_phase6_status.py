"""GUI Phase 6 — Sources / Validation / System Health contracts.

The workspace must read the canonical health artifact
(data/source_health.json with summary/sources) through core state using its
real fields (status online/failed, consecutiveFailures, onlineWithData);
state filters must show real counts; search must stay honest with empty
states; severity must follow the shared language.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_status_reads_canonical_health_with_honest_states():
    text = (ROOT / 'js/modules/status.js').read_text(encoding='utf-8')
    assert 'export function renderStatus' in text
    assert 'sourceHealth' in text
    assert 'getState()' in text
    assert 'escapeHtml' in text
    assert 'Loading source health' in text
    assert 'Source health unavailable' in text
    assert 'lorem' not in text.lower()


def test_status_binds_real_artifact_fields_not_placeholders():
    text = (ROOT / 'js/modules/status.js').read_text(encoding='utf-8')
    for field in ('onlineWithData', 'consecutiveFailures', 'contentStatus', 'freshnessMinutes'):
        assert field in text, f'workspace never binds real field {field}'
    assert "'online'" in text or '"online"' in text, 'workspace must match the artifact status vocabulary'
    assert 'statusDot' not in text and 'globalLastUpdated' not in text, 'dead shell hooks must go'


def test_status_filters_counts_search_and_empty_states():
    text = (ROOT / 'js/modules/status.js').read_text(encoding='utf-8')
    assert 'data-status-filter' in text
    assert 'statusSearch' in text
    assert 'statusBody' in text
    assert 'statusMore' in text
    assert 'No sources match' in text
    assert 'Showing' in text, 'workspace must report shown/total counts honestly'
    assert 'sev-' in text, 'workspace must use shared severity language'
    for level in ('healthy', 'watch', 'critical'):
        assert level in text, f'workspace never selects severity {level}'


def test_phase6_shell_and_boot_wiring():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="section-status"' in html
    assert 'id="statusBody"' in html
    assert 'id="statusUpdated"' in html
    assert 'data-nav="status"' in html
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/status.js' in app
    assert 'renderStatus' in app
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert './data/source_health.json' in config
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'sourceHealth' in state
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'sourceHealth' in fetch


def test_phase6_styles_and_pages_safety():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('gp-source-row', 'gp-source-chip', 'gp-source-summary', 'gp-source-controls'):
        assert token in css, f'stylesheet missing {token}'
    assert 'sev-healthy' in css and 'sev-critical' in css
    text = (ROOT / 'js/modules/status.js').read_text(encoding='utf-8')
    assert 'href="/' not in text and 'src="/' not in text
    assert '/Aegis-Nexus/' not in text
