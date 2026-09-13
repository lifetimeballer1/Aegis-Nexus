"""Fleet-B deep fidelity: stale, empty, missing assets, mobile, source detail."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def _t():
    return (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
def _css():
    return (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
def _html():
    return (ROOT / 'index.html').read_text(encoding='utf-8')
def test_source_fail_detail_rendered():
    t = _t()
    assert 'consecutiveFailures' in t
    assert 'consecutive failures' in t.lower()
def test_empty_snapshot_graceful():
    t = _t()
    assert 'Command overview unavailable' in t
    assert 'Loading command overview' in t
def test_stale_offline_banners_honest():
    t = _t()
    assert 'showing cached data' in t.lower()
    assert 'Cached snapshot shown' in t or 'cached snapshot' in t.lower()
    assert 'feedMeta' in t
def test_missing_assets_tile_fallback():
    t = _t()
    assert 'tileerror' in t.lower() or 'fallback' in t.lower()
    assert 'openstreetmap' in t.lower()
    assert 'dark operational basemap' in t.lower() or 'dark operational' in t.lower()
def test_headline_relative_time_fallback():
    t = _t()
    assert 'formatRelativeTime' in t
    assert 'itemTime' in t or 'eventTime' in t
def test_market_cards_bounded_eight():
    t = _t()
    assert 'slice(0, 8)' in t
    assert 'cc-mkt-card' in t
def test_mobile_shell_usable():
    css = _css()
    assert '@media' in css
    assert 'cc-grid' in css or 'cc-kpi-strip' in css
def test_shell_hooks_no_hardcoded_repo():
    t = _t()
    html = _html()
    assert 'dashboardBody' in html
    assert '/Aegis-Nexus/' not in t
    assert 'lorem' not in t.lower()
def test_ops_trend_sparkline():
    t = _t()
    assert "sparklineSVG" in t
    assert "Tension history trend" in t
def test_what_changed_empty_note():
    t = _t()
    assert "wcEmptyNote" in t
    assert "Since last refresh" in t
def test_kpi_spark_values():
    t = _t()
    assert "evSpark" in t
    assert "gp-nums" in t
def test_domain_rows_bar():
    t = _t()
    assert "cc-domain-row" in t
    assert "cc-domain-bar" in t
def test_region_table_wrap():
    t = _t()
    assert "cc-table-wrap" in t
    assert "cc-table" in t
def test_pulse_freshness():
    t = _t()
    assert "Feed freshness" in t
    assert "Signal pulse" in t
def test_headline_thumb_time():
    t = _t()
    assert "cc-thumb" in t
    assert "cc-time" in t
def test_search_focus_restore():
    t = _t()
    assert "setSelectionRange" in t
    assert "renderDashboard" in t
