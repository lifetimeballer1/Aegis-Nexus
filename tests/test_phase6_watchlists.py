"""Phase 6 — acknowledgement status + my-watchlist contracts.

Ack status must list acknowledged alerts with honest queue-membership;
watchlist pins must be device-local and resolve live levels against the
current pipeline brief. Team/routing/delivery backends do not exist and
must not be faked.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ack_status_table_is_wired():
    text = (ROOT / 'js/modules/alerts.js').read_text(encoding='utf-8')
    assert 'Acknowledgement Status' in text
    assert 'data-ack-clear' in text
    assert 'rotated out of queue' in text
    assert 'unacked critical/high' in text
    assert 'this device only' in text


def test_my_watchlist_pins_and_export():
    text = (ROOT / 'js/modules/briefings.js').read_text(encoding='utf-8')
    assert 'gp.mywatch.v1' in text
    assert 'My Watchlist' in text
    assert 'data-watch-pin' in text
    assert 'data-watch-unpin' in text
    assert 'data-watch-export' in text
    assert 'not in the current brief' in text
    assert 'Team Watchlist' not in text, 'no team backend exists; must not be faked'
    assert 'Delivery Channels' not in text, 'no delivery backend exists; must not be faked'
    assert 'lorem' not in text.lower()
