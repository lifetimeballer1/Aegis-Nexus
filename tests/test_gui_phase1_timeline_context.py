"""GUI Phase 1 tranche 3 — timeline rail paired with tension/alerts context.

Concept 05 pairs the timeline rail with tension/alerts context; the rail stood
alone. Locks the item-6 joins in js/modules/timeline.js: every entry carries
its tension-at-the-time (latest canonical historicalTrends sample at or before
the point — never interpolated) plus its linked alerts count (canonical alert
timestamps within +/-24h), a phone-only tension strip above the rail (DOM order
strip -> rail -> reading pane; hidden on desktop), and the T2 reading-pane
drawer wiring intact. Also re-verifies the T2 drawer controller by structural
re-read (balanced braces/parens, complete exports) since node is unavailable.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def test_timeline_joins_tension_at_time():
    js = _read('js/modules/timeline.js')
    assert 'historicalTrends' in js, 'no canonical tension-series join'
    assert 'tensionAt' in js, 'no tension-at-the-time resolver'
    assert 'tension n/a' in js, 'no honest fallback when point predates samples'


def test_timeline_joins_linked_alerts():
    js = _read('js/modules/timeline.js')
    assert 'linkedAlertCount' in js, 'no linked-alerts join'
    assert 'lastSignal' in js, 'conflict alert timestamps not joined'
    assert 'lastSeen' in js, 'map-event alert timestamps not joined'
    assert 'ALERT_LINK_WINDOW_MS' in js, 'no bounded link window'
    assert 'no alerts' in js, 'no honest zero-alerts state'


def test_timeline_entries_carry_context():
    js = _read('js/modules/timeline.js')
    assert 'entryContext' in js, 'no per-entry context formatter'
    assert 'entryContext(p)' in js, 'row meta does not carry context'


def test_timeline_phone_order_strip_then_rail_then_pane():
    js = _read('js/modules/timeline.js')
    asm = js[js.index('el.innerHTML = '):]
    strip = asm.index('${strip}')
    rail = asm.index('gp-timeline-rail')
    pane = asm.index('${pane}')
    assert strip < rail < pane, 'phone order must be tension strip, then rail, then reading pane'
    assert '#section-alerts' in js, 'no link pairing rail context to Alerts'


def test_timeline_tension_strip_phone_only():
    css = _read('css/dashboard.css')
    assert '.gp-tl-tension' in css, 'missing tension strip style'
    assert '@media(min-width:1024px)' in css, 'no desktop rule'
    desktop_rule = css[css.index('@media(min-width:1024px)', css.index('.gp-tl-tension')):]
    assert '.gp-tl-tension' in desktop_rule.split('}')[0] + desktop_rule.split('}')[1], \
        'strip not hidden on desktop (desktop must stay unchanged)'


def test_timeline_reading_pane_still_drawer():
    js = _read('js/modules/timeline.js')
    assert 'tlReadingPane' in js
    assert 'gp-drawer' in js
    assert 'openDrawer' in js
    assert 'View in Alerts' in js, 'reading pane lacks alerts pairing link'


def test_drawer_controller_structurally_sound():
    # T2 caveat re-verification without node: careful re-read — balanced
    # delimiters, complete exports, no truncation.
    js = _read('js/core/drawer.js')
    assert js.count('{') == js.count('}'), 'unbalanced braces in drawer.js'
    assert js.count('(') == js.count(')'), 'unbalanced parens in drawer.js'
    assert js.count('[') == js.count(']'), 'unbalanced brackets in drawer.js'
    for name in ('openDrawer', 'closeDrawer', 'closeAllDrawers', 'initDrawers', 'isPhoneDrawer'):
        assert name in js, 'drawer.js lacks %s' % name
    assert js.rstrip().endswith('}'), 'drawer.js looks truncated'
