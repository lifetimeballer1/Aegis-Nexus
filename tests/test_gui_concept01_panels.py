"""Fleet-B Concept01 remaining panels: signals, tension, domain, ops, pulse, wc."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def _t():
    return (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
def test_top_signals_panel():
    t = _t()
    assert 'Top Signals' in t
    assert 'cc-signal-row' in t
    assert 'No signals in snapshot' in t
def test_tension_deep_dive_panel():
    t = _t()
    assert 'Tension Deep Dive' in t
    assert 'tension' in t.lower()
    assert 'No trend history' in t
def test_domain_mix_panel():
    t = _t()
    assert 'Domain Mix' in t
    assert 'Last 60 headlines' in t
    assert 'No domain data' in t
def test_ops_strip_tiles():
    t = _t()
    assert 'Operations at a glance' in t
    for k in ('Tension index', 'Sources online', 'Stale feeds', 'Market signals'):
        assert k in t, f'missing ops tile {k}'
def test_pulse_row_metrics():
    t = _t()
    assert 'Signal pulse' in t
    for k in ('Signals 24h', 'Critical share', 'Avg reports', 'Feed freshness'):
        assert k in t, f'missing pulse {k}'
def test_what_changed_counts_block():
    t = _t()
    for k in ('New events added', 'Events escalated', 'Sources reporting', 'Sources failed', 'Significant indicator moves'):
        assert k in t, f'missing wc block {k}'
def test_global_map_panel():
    t = _t()
    assert "Global Map" in t
    assert "View Full Map" in t
    assert "Map period" in t
def test_source_health_panel_link():
    t = _t()
    assert "View Sources" in t
    assert "sources online" in t
def test_market_panel_link():
    t = _t()
    assert "View Markets" in t
    assert "cc-mkt" in t
def test_headline_live_badge():
    t = _t()
    assert "cs-live-badge" in t
    assert "NO FEED" in t
def test_mini_map_block():
    t = _t()
    assert "dashMap" in t
    assert "Mini operational map" in t
def test_tension_big_number():
    t = _t()
    assert "cc-tension-big" in t
    assert "cc-tension-delta" in t
def test_regions_map_link():
    t = _t()
    assert "section-map" in t
    assert "cc-table" in t
