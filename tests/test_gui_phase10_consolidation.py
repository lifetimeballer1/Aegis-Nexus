"""GUI Phase 10 — shared design-token consolidation contracts."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSS_FILES = tuple(ROOT.glob('*.css')) + tuple((ROOT / 'css').glob('*.css'))


def css_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def definitions(name: str) -> list[Path]:
    pattern = re.compile(rf'(?<![-\w]){re.escape(name)}\s*:')
    return [path for path in CSS_FILES if pattern.search(css_text(path))]


def test_shared_severity_tokens_have_one_canonical_owner():
    tokens = css_text(ROOT / 'css/tokens.css')
    expected = {
        '--sev-info': 'var(--blue)',
        '--sev-watch': 'var(--amber)',
        '--sev-critical': 'var(--red)',
        '--sev-healthy': 'var(--green)',
    }
    for name, value in expected.items():
        assert definitions(name) == [ROOT / 'css/tokens.css']
        assert re.search(rf'{re.escape(name)}\s*:\s*{re.escape(value)}\s*;', tokens)


def test_legacy_aliases_point_to_canonical_tokens():
    tokens = css_text(ROOT / 'css/tokens.css')
    aliases = {
        '--panel2': 'var(--panel-2)',
        '--gp-border': 'var(--line)',
        '--gp-panel': 'var(--panel)',
        '--gp-panel-alt': 'var(--panel-2)',
        '--gp-text': 'var(--text)',
        '--gp-muted': 'var(--muted)',
        '--gp-conflict': 'var(--red)',
        '--gp-energy': 'var(--orange)',
        '--gp-economic': 'var(--amber)',
        '--gp-strategic': 'var(--blue)',
        '--gp-political': 'var(--purple)',
        '--gp-resource': 'var(--green)',
    }
    for name, value in aliases.items():
        assert definitions(name) == [ROOT / 'css/tokens.css']
        assert re.search(rf'{re.escape(name)}\s*:\s*{re.escape(value)}\s*;', tokens)


def test_token_stylesheet_loads_before_all_consumers():
    html = css_text(ROOT / 'index.html')
    order = [
        html.index('css/tokens.css'),
        html.index('css/components.css'),
        html.index('css/dashboard.css'),
        html.index('global_pulse_tokens.css'),
    ]
    assert order == sorted(order)


def test_compatibility_stylesheet_does_not_redeclare_root_tokens():
    compatibility = css_text(ROOT / 'global_pulse_tokens.css')
    assert ':root' not in compatibility
    assert 'Canonical tokens and aliases live in css/tokens.css' in compatibility


def test_intelligence_web_consumes_canonical_tokens_without_redeclaring_them():
    web = css_text(ROOT / 'intelligence-web.html')
    assert '<link rel="stylesheet" href="css/tokens.css">' in web
    for name in ('--bg', '--line', '--text', '--muted', '--blue', '--green', '--amber', '--red',
                 '--sev-info', '--sev-watch', '--sev-critical', '--sev-healthy'):
        assert not re.search(rf'{re.escape(name)}\s*:', web), f'Intelligence Web redeclares {name}'


def test_shared_severity_module_owns_artifact_value_mappings():
    core = css_text(ROOT / 'js/core/severity.js')
    assert 'export function confidenceSeverity' in core
    assert 'export function escalationSeverity' in core
    assert 'export function watchLevelSeverity' in core
    for module in ('alerts.js', 'timeline.js', 'briefings.js'):
        text = css_text(ROOT / 'js/modules' / module)
        assert "../core/severity.js" in text
    assert "raw.includes('high')" not in css_text(ROOT / 'js/modules/alerts.js')
    assert "raw.includes('high')" not in css_text(ROOT / 'js/modules/timeline.js')
    assert "raw.includes('high')" not in css_text(ROOT / 'js/modules/briefings.js')


def test_status_chip_compatibility_classes_cover_operational_severity():
    dashboard = css_text(ROOT / 'css/dashboard.css')
    assert '.gp-sev-watch' in dashboard
    assert '.gp-sev-info' in dashboard
    assert '.gp-sev-healthy' in dashboard
    assert 'color:var(--sev-watch)' in dashboard
    assert 'color:var(--sev-info)' in dashboard
    assert 'color:var(--sev-healthy)' in dashboard
