"""GUI Phase 4 — Intelligence Brain Workspace contracts.

The workspace must read the canonical brain artifact
(data/intelligence_brain.json with nodes/edges/stats) through core state,
with the snapshot-embedded copy as fallback only; node severity must follow
the shared language; selection, evidence, and map cross-talk must stay wired.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_brain_reads_canonical_artifact_with_honest_states():
    text = (ROOT / 'js/modules/intelligence-brain.js').read_text(encoding='utf-8')
    assert 'export function renderIntelligenceBrain' in text
    assert 'intelligenceBrain' in text, 'workspace never reads state.intelligenceBrain'
    assert 'getState()' in text
    assert 'escapeHtml' in text
    assert 'Loading intelligence workspace' in text
    assert 'Intelligence Brain unavailable' in text
    assert 'lorem' not in text.lower()


def test_brain_severity_selection_and_evidence_are_wired():
    text = (ROOT / 'js/modules/intelligence-brain.js').read_text(encoding='utf-8')
    assert 'data-brain-node' in text
    assert 'sev-' in text, 'workspace must use shared severity language'
    for kind in ('conflict', 'cartel', 'chokepoint', 'economic', 'country'):
        assert kind in text, f'workspace never maps kind {kind} to severity'
    assert 'gp:brain-select' in text, 'map cross-talk must stay wired'
    assert 'Showing' in text, 'workspace must report shown/total counts honestly'
    assert 'No Brain nodes match' in text


def test_phase4_shell_and_boot_wiring():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'id="section-brain"' in html
    assert 'id="brainBody"' in html
    assert 'id="brainUpdated"' in html
    assert 'data-nav="brain"' in html
    app = (ROOT / 'js/app.js').read_text(encoding='utf-8')
    assert './modules/intelligence-brain.js' in app
    assert 'renderIntelligenceBrain' in app
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert './data/intelligence_brain.json' in config
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'intelligenceBrain' in state
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'intelligenceBrain' in fetch


def test_phase4_styles_and_pages_safety():
    css = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    for token in ('gp-brain-node', 'sev-critical', 'sev-watch', 'sev-info'):
        assert token in css, f'stylesheet missing {token}'
    for name in ('js/modules/intelligence-brain.js', 'js/modules/brain-timeline.js'):
        text = (ROOT / name).read_text(encoding='utf-8')
        assert 'href="/' not in text and 'src="/' not in text
        assert '/Aegis-Nexus/' not in text
