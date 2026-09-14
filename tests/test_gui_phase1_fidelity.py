"""GUI Phase 1 fidelity tranche 1 — section-header freshness parity.

Concept 01/05/06 refs carry a freshness line in every section header.
Dashboard, briefings, map, search and status already stamp theirs;
alerts, timeline and markets did not. Locks the three stamps added in
this tranche: header divs in index.html + wiring in the driving module.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _html():
    return (ROOT / 'index.html').read_text(encoding='utf-8')


def test_alerts_header_stamp_exists():
    html = _html()
    assert 'id="section-alerts"' in html
    assert 'id="alertsUpdated"' in html, 'alerts header lacks freshness stamp'


def test_timeline_header_stamp_exists():
    html = _html()
    assert 'id="section-timeline"' in html
    assert 'id="timelineUpdated"' in html, 'timeline header lacks freshness stamp'


def test_markets_header_stamp_exists():
    html = _html()
    assert 'id="section-markets"' in html
    assert 'id="marketsUpdated"' in html, 'markets header lacks freshness stamp'


def test_alerts_wires_stamp():
    text = (ROOT / 'js/modules/alerts.js').read_text(encoding='utf-8')
    assert "getElementById('alertsUpdated')" in text, 'renderAlerts never paints the stamp'


def test_timeline_wires_stamp():
    text = (ROOT / 'js/modules/timeline.js').read_text(encoding='utf-8')
    assert "getElementById('timelineUpdated')" in text, 'renderTimeline never paints the stamp'


def test_markets_wires_stamp():
    text = (ROOT / 'js/modules/markets.js').read_text(encoding='utf-8')
    assert "getElementById('marketsUpdated')" in text, 'renderMarkets never paints the stamp'
