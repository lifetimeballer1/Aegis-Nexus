"""GUI Phase 8 — Universal Search contracts.

One query must scan the already-wired canonical state (stories, conflicts,
events, Brain nodes, Web entities, map signals, brief records) with real
per-domain counts; results must deep-link to home sections; Brain/Web hits
must refocus those workspaces via gp:brain-select. Nothing is fabricated:
unloaded domains and empty queries render honest states.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_search_scans_wired_state_with_honest_states():
    text = (ROOT / 'js/modules/search.js').read_text(encoding='utf-8')
    assert 'export function renderSearch' in text
    assert 'getState()' in text
    assert 'escapeHtml' in text
    assert 'Loading search index' in text
    assert 'Search unavailable' in text
    assert 'Type at least 2 characters' in text
    assert 'No results match' in text
    assert 'lorem' not in text.lower()


def test_search_covers_all_domains_with_real_counts():
    text = (ROOT / 'js/modules/search.js').read_text(encoding='utf-8')
    for field in ('liveArticles', 'snapshot', 'mapData', 'intelligenceBrain', 'intelligenceGraph', 'mapPoints', 'intelligenceBrief'):
        assert field in text, f'search never scans {field}'
    for domain in ('stories', 'conflicts', 'events', 'brain', 'web', 'map', 'brief'):
        assert domain in text, f'search never covers domain {domain}'
    assert 'total matches' in text or 'total' in text
    assert 'records indexed' in text, 'search must report honest index size'


def test_search_deep_links_and_workspace_refocus():
    text = (ROOT / 'js/modules/search.js').read_text(encoding='utf-8')
    for section in ('#section-breaking', '#section-conflicts', '#section-alerts', '#section-brain', '#section-intelweb', '#section-map', '#section-briefings'):
        assert section in text, f'search never links to {section}'
    assert 'gp:brain-select' in text, 'node hits must refocus Brain/Web/Map workspaces'
    assert 'data-search-brain' in text
    assert 'target="_blank" rel="noopener noreferrer"' in text, 'external story links must be safe'


def test_phase8_shell_and_boot_wiring():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="section-search"' in html
    assert 'id="searchBody"' in html
    assert 'id="searchUpdated"' in html
    assert 'data-nav="search"' in html
    assert html.count('data-nav="search"') >= 2, 'search nav must exist in command tabs and bottom nav'
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/search.js' in app
    assert 'renderSearch' in app
    assert "'searchBody'" in app or '"searchBody"' in app


def test_phase8_styles_and_pages_safety():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('gp-search-group', 'gp-search-row'):
        assert token in css, f'stylesheet missing {token}'
    text = (ROOT / 'js/modules/search.js').read_text(encoding='utf-8')
    assert 'href="/' not in text and 'src="/' not in text
    assert '/Aegis-Nexus/' not in text
