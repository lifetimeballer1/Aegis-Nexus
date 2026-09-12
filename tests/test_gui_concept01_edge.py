"""Fleet-B Concept01 edge contracts: headlines, regions, what-changed, pulse, health, mobile."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def _t():
    return (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
def _css():
    return (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
def test_headline_intel_live_filter_empty():
    t = _t()
    assert 'Headline Intelligence' in t
    assert 'dashSearch' in t
    assert 'Filter headlines' in t
    assert 'No recent reports' in t
    assert 'LIVE' in t
def test_priority_regions_table_contract():
    t = _t()
    assert 'Priority Regions' in t
    for h in ('Activity', 'Impact', 'Trend'):
        assert h in t
    assert 'No regional data' in t
def test_what_changed_window_summary():
    t = _t()
    assert 'What Changed' in t
    assert 'Since last refresh' in t or 'current window' in t
    for k in ('newEvents', 'escalated', 'indicatorMoves'):
        assert k in t, f'missing what-changed field {k}'
def test_market_pulse_delayed_cards():
    t = _t()
    assert 'Market Pulse' in t
    assert 'DELAYED' in t
    assert 'Market data unavailable' in t
    assert 'slice(0, 8)' in t or 'cc-mkt-card' in t
def test_source_health_donut_counts():
    t = _t()
    assert 'Source Health' in t
    assert 'Source health unavailable' in t or 'Source health' in t
    for w in ('Online', 'Degraded', 'Offline'):
        assert w in t, f'missing health row {w}'
    assert 'consecutiveFailures' in t
def test_mobile_stale_offline_edge():
    t = _t()
    css = _css()
    assert '@media' in css
    assert 'overflow-x:auto' in css
    assert 'overflow-wrap' in css
    assert 'Offline' in t
    assert 'stale' in t.lower()
    assert 'href="/' not in t
    assert '/Aegis-Nexus/' not in t
def test_headline_rows_capped_pills():
    t = _t()
    assert "cc-head" in t
    assert "cc-rank" in t
    assert "slice(0, 6)" in t
def test_severity_legend_copy():
    t = _t()
    assert "Severity legend" in t
    assert "Blue = Informational" in t
    assert "Red = Critical" in t
def test_tension_meta_honest():
    t = _t()
    assert "Global tension index" in t
    assert "Last updated:" in t
    assert "All Systems Operational" in t
def test_signal_rows_reports():
    t = _t()
    assert "cc-signal-row" in t
    assert "cs-strip-dot" in t
    assert "reports" in t
def test_domain_sample_cap():
    t = _t()
    assert "slice(0, 60)" in t
    assert "catPill" in t
def test_regions_six_cap():
    t = _t()
    assert "order.slice(0, 6)" in t
    assert "cc-table" in t
