"""GUI Phase 1 tranche 4 — markets tab filter/sort (audit item 6b/7).

The Markets tab was a flat grid with no way to isolate a category or
re-order cards. Locks the T4 joins in js/modules/markets.js: category
buckets derived from the public symbols file (update_market_data.py WATCH
kinds + each symbol's own name/ticker text — no outside taxonomy), filter
chips with live counts (alerts-style gp-filter), a movers | A-Z sort
toggle, an honest empty state for empty buckets (Agri has no contracts in
the feed), and the T1 freshness stamp + DELAYED + disclaimer intact.
Phone-first chip scroll; desktop grid untouched.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def test_market_buckets_derived_from_symbols_file():
    js = _read('js/modules/markets.js')
    assert 'marketBucket' in js, 'no category resolver'
    # Kinds straight from update_market_data.py WATCH — no invented taxonomy.
    for kind in ("'fx'", "'rates'", 'commodity'):
        assert kind in js, 'bucket resolver ignores WATCH kind %s' % kind
    for bucket in ("'energy'", "'metals'", "'macro-fx'", "'agri'", "'other'"):
        assert bucket in js, 'missing bucket %s' % bucket
    # Spot checks against the real feed names/symbols.
    assert 'WTI' in js or 'wti' in js, 'WTI Crude not mapped to Energy'
    assert 'gold' in js, 'Gold not mapped to Metals'
    assert 'yield' in js, '10Y Yield not mapped to Macro-FX'


def test_market_filter_chips_with_live_counts():
    js = _read('js/modules/markets.js')
    for name in ('All', 'Energy', 'Metals', 'Macro-FX', 'Agri'):
        assert name in js, 'missing filter chip %s' % name
    assert 'data-market-filter' in js, 'no filter wiring'
    assert 'aria-pressed' in js, 'chips lack pressed state'
    assert 'counts[key]' in js or 'counts[' in js, 'chips lack live counts'
    assert 'gp-filter-row' in js and 'gp-mkt-filters' in js, 'no filter row'


def test_market_sort_toggle_movers_and_az():
    js = _read('js/modules/markets.js')
    assert 'data-market-sort' in js, 'no sort wiring'
    assert 'movers' in js, 'no movers sort'
    assert 'az' in js, 'no A-Z sort'
    assert 'localeCompare' in js, 'A-Z is not alphabetical'
    assert 'Math.abs' in js, 'movers is not |change| ranked'
    assert 'Sort markets' in js, 'sort group lacks accessible label'


def test_market_empty_bucket_honest_state():
    js = _read('js/modules/markets.js')
    assert 'No ${escapeHtml(label)} indicators' in js or 'No ' in js and 'matches this filter' in js, \
        'no honest empty-filter state'


def test_market_freshness_and_disclaimer_intact():
    js = _read('js/modules/markets.js')
    assert 'marketsUpdated' in js, 'T1 freshness stamp wiring lost'
    assert 'DELAYED' in js, 'DELAYED badge lost'
    assert 'not real-time trading data or investment advice' in js, 'disclaimer lost'
    assert 'gp-grid gp-grid-3' in js, 'desktop card grid changed'
    assert 'gpMarketsMore' in js, 'see-more paging lost'


def test_market_filters_phone_scroll_desktop_untouched():
    css = _read('css/dashboard.css')
    assert '.gp-mkt-filters' in css, 'missing phone filter-scroll rule'
    assert '1023' in css, 'no sub-1024px phone rule'
    desktop_rules = [line for line in css.splitlines() if 'min-width:1024px' in line]
    assert not any('gp-mkt-' in line for line in desktop_rules), \
        'filters must stay visible on desktop (desktop unchanged)'
