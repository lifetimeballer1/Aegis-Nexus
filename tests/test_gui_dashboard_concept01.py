"""Fleet-B Concept01 dashboard map-period + KPI contracts (text-only, no browser)."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def _t():
    return (ROOT / 'js/modules/dashboard.js').read_text(encoding='utf-8')
def test_map_period_buttons_present():
    t = _t()
    assert 'MAP_PERIODS' in t
    for p in ('24H', '7D', '30D'):
        assert p in t, f'missing period {p}'
    assert 'data-dash-period' in t or 'dash-period' in t
def test_map_view_getter_setter_exports():
    t = _t()
    assert 'getDashboardMapView' in t
    assert 'setDashboardMapView' in t
    assert 'export function getDashboardMapView' in t
    assert 'export function setDashboardMapView' in t
def test_map_window_time_filtering_honest():
    t = _t()
    assert 'inMapWindow' in t
    assert 'eventTime' in t
    for k in ('lastSeen', 'firstSeen'):
        assert k in t, f'honest time field {k} missing'
def test_map_empty_window_guidance():
    t = _t()
    low = t.lower()
    assert ('no dated signals' in low or 'try 7d' in low or 'no signals in this window' in low)
def test_map_undated_footnote_disclosed():
    t = _t()
    assert 'undated' in t.lower()
def test_kpi_strip_six_concepts():
    t = _t()
    for label in ('Active Events', 'High Priority', 'Emerging', 'Critical', 'Monitored Regions', 'Sources Online'):
        assert label in t, f'KPI missing {label}'
    assert 'cc-kpi-strip' in t
    assert 'listitem' in t
def test_map_period_buttons_mirror_state():
    t = _t()
    assert "aria-pressed" in t
    assert "p === mapPeriod" in t

def test_map_search_preserves_query():
    t = _t()
    assert "dashSearch" in t
    assert "esc(query)" in t
def test_kpi_tile_subtitles():
    t = _t()
    assert "tracked clusters" in t
    assert "escalated conflicts" in t
    assert "low-confidence events" in t
    assert "high-confidence events" in t
    assert "reporting feeds" in t
def test_map_window_count_subtitle():
    t = _t()
    assert "dark operational basemap" in t
    assert "mapInWindow.length" in t
def test_dashboard_live_region_and_kpi_label():
    t = _t()
    assert "aria-live" in t
    assert "Key indicators" in t
    assert "Map legend" in t
