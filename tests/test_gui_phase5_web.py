"""GUI Phase 5 — Intelligence Web Explorer contracts.

The explorer must read the canonical relationship graph
(data/intelligence_graph.json with nodes/edges) through core state, with
Brain overlay from state; type filters must reflect real graph types;
search must stay honest with empty states; the 3D engine must stay opt-in
so mobile deferred loading holds; the lazy standalone frame is preserved.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_web_reads_canonical_graph_with_honest_states():
    text = (ROOT / 'js/modules/intelligence-web.js').read_text(encoding='utf-8')
    assert 'export function renderIntelligenceWeb' in text
    assert 'intelligenceGraph' in text, 'explorer never reads state.intelligenceGraph'
    assert 'intelligenceBrain' in text, 'explorer never layers the Brain overlay'
    assert 'getState()' in text
    assert 'escapeHtml' in text
    assert 'Loading relationship web' in text
    assert 'Intelligence Web not available' in text
    assert 'lorem' not in text.lower()


def test_web_filters_search_severity_and_detail_are_wired():
    text = (ROOT / 'js/modules/intelligence-web.js').read_text(encoding='utf-8')
    assert 'gpWebSearch' in text
    assert 'gpWebType' in text
    assert 'intelwebBody' in text
    assert 'data-web-node' in text
    assert 'No entities match' in text
    assert 'Showing' in text, 'explorer must report shown/total counts honestly'
    assert 'sev-' in text, 'explorer must use shared severity language'
    for typ in ('conflict', 'military', 'cartel', 'political', 'strategic'):
        assert typ in text, f'explorer never maps type {typ} to severity'
    assert 'gp:brain-select' in text, 'Brain cross-talk must stay wired'


def test_web_keeps_3d_opt_in_and_lazy_frame():
    text = (ROOT / 'js/modules/intelligence-web.js').read_text(encoding='utf-8')
    assert 'gpWebLoad3d' in text, '3D engine must be opt-in, not automatic'
    assert 'Loading 3D engine' in text
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'class="gp-intelweb-frame"' in html
    assert 'loading="lazy"' in html, 'standalone 3D frame must stay lazy'


def test_phase5_shell_and_boot_wiring():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="section-intelweb"' in html
    assert 'id="intelwebBody"' in html
    assert 'id="intelwebUpdated"' in html
    assert 'data-nav="intelweb"' in html
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/intelligence-web.js' in app
    assert 'renderIntelligenceWeb' in app
    assert "'intelwebBody'" in app or '"intelwebBody"' in app
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert './data/intelligence_graph.json' in config
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'intelligenceGraph' in state
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'intelligenceGraph' in fetch


def test_phase5_styles_and_pages_safety():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('gp-web-controls', 'gp-web-node', 'gp-intelweb-detail'):
        assert token in css, f'stylesheet missing {token}'
    assert 'sev-critical' in css and 'sev-watch' in css
    text = (ROOT / 'js/modules/intelligence-web.js').read_text(encoding='utf-8')
    assert 'href="/' not in text and 'src="/' not in text
    assert '/Aegis-Nexus/' not in text
