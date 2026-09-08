"""GUI Phase 7 — Intelligence Briefings contracts.

The workspace must read the canonical deterministic brief
(data/intelligence_brief.json with headline/topDevelopments/watchlist/
methodology/freshness) through core state; severity may only derive from
artifact fields (breaking, confidence, watchlist level); category filters
must show real counts; undated records must not be invented.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_briefings_reads_canonical_brief_with_honest_states():
    text = (ROOT / 'js/modules/briefings.js').read_text(encoding='utf-8')
    assert 'export function renderBriefings' in text
    assert 'intelligenceBrief' in text, 'workspace never reads state.intelligenceBrief'
    assert 'getState()' in text
    assert 'escapeHtml' in text
    assert 'Loading intelligence brief' in text
    assert 'Brief unavailable' in text
    assert 'lorem' not in text.lower()


def test_briefings_binds_real_artifact_fields_not_placeholders():
    text = (ROOT / 'js/modules/briefings.js').read_text(encoding='utf-8')
    for field in ('topDevelopments', 'watchlist', 'methodology', 'freshness', 'independentSourceCount', 'reportCount', 'topFactors', 'evidenceCount'):
        assert field in text, f'workspace never binds real field {field}'
    assert 'breaking' in text
    assert 'confidence' in text
    assert 'Mock' not in text


def test_briefings_filters_counts_expansion_and_empty_states():
    text = (ROOT / 'js/modules/briefings.js').read_text(encoding='utf-8')
    assert 'data-brief-filter' in text
    assert 'briefingsBody' in text
    assert 'briefMore' in text
    assert 'No developments match' in text
    assert 'Watchlist empty' in text
    assert 'Showing' in text, 'workspace must report shown/total counts honestly'
    assert 'sev-' in text, 'workspace must use shared severity language'


def test_phase7_shell_and_boot_wiring():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="section-briefings"' in html
    assert 'id="briefingsBody"' in html
    assert 'id="briefingsUpdated"' in html
    assert 'data-nav="briefings"' in html
    assert html.count('data-nav="briefings"') >= 2, 'briefings nav must exist in command tabs and bottom nav'
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/briefings.js' in app
    assert 'renderBriefings' in app
    assert "'briefingsBody'" in app or '"briefingsBody"' in app
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert './data/intelligence_brief.json' in config
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'intelligenceBrief' in state
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'intelligenceBrief' in fetch


def test_phase7_styles_and_pages_safety():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('gp-brief-dev', 'gp-brief-watch', 'gp-brief-level', 'gp-brief-caution', 'gp-brief-h'):
        assert token in css, f'stylesheet missing {token}'
    assert 'sev-critical' in css and 'sev-watch' in css
    text = (ROOT / 'js/modules/briefings.js').read_text(encoding='utf-8')
    assert 'href="/' not in text and 'src="/' not in text
    assert '/Aegis-Nexus/' not in text
