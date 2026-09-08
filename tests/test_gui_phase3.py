"""GUI Phase 3 — Sources & System Health contracts.

The upgraded status section must render the real registry, collector
telemetry, and manifest hashes; health badges must reflect the pipeline's
actual status vocabulary (online/failing/degraded), never a value the
pipeline does not emit.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_status_renders_registry_telemetry_and_manifest():
    text = (ROOT / 'js/modules/status.js').read_text(encoding='utf-8')
    assert 'export function renderStatus' in text
    assert 'srcRegistry' in text
    assert 'srcSearch' in text
    assert 'data-src-filter' in text
    assert 'failedSources' in text
    assert 'refreshManifest' in text or 'manifest' in text
    assert 'sha256' in text
    assert 'escapeHtml' in text
    assert 'lorem' not in text.lower()


def test_status_badges_match_pipeline_vocabulary():
    text = (ROOT / 'js/modules/status.js').read_text(encoding='utf-8')
    assert "'online'" in text or '"online"' in text
    assert "'failed'" in text or '"failed"' in text
    assert 'Failing' in text
    assert 'Degraded' in text
    assert "=== 'ok'" not in text and '=== "ok"' not in text


def test_phase3_data_layer_and_shell():
    config = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    assert './data/live_status.json' in config
    assert './data/refresh_manifest.json' in config
    state = (ROOT / 'js/core/state.js').read_text(encoding='utf-8')
    assert 'liveStatus' in state
    assert 'refreshManifest' in state
    fetch = (ROOT / 'js/core/fetch.js').read_text(encoding='utf-8')
    assert 'liveStatus' in fetch
    assert 'refreshManifest' in fetch
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'Sources &amp; System Health' in html
    assert 'id="statusBody"' in html


def test_markets_module_parses_and_links_sources():
    text = (ROOT / 'js/modules/markets.js').read_text(encoding='utf-8')
    assert 'export function renderMarkets' in text
    assert '/^https?:\\/\\//i' in text
    assert '\\\\/' not in text


def test_phase3_pages_safety():
    text = (ROOT / 'js/modules/status.js').read_text(encoding='utf-8')
    assert 'href="/' not in text and "src=\"/" not in text
    assert '/Aegis-Nexus/' not in text
