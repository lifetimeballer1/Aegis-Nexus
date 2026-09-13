"""Mobile tab order — Command Center, Conflict Watch, Map, Intel Web lead on mobile.

Locks the mobile-only reorder: a max-width media query assigns flex
 so the first viewport leads with Command Center, then Conflict
Map, then Intel Web. Desktop CSS outside media queries must not set
 on these sections/nav items, and all ids / data-nav hooks stay
stable.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAD = ['dashboard', 'conflicts', 'map', 'intelweb']


def _layout_css():
    return (ROOT / 'css/layout.css').read_text(encoding='utf-8')


def _mobile_block(css):
    idx = css.find('MOBILE TAB ORDER')
    assert idx != -1, 'mobile-order block missing from css/layout.css'
    start = css.find('{', css.find('@media', idx))
    depth = 0
    for pos in range(start, len(css)):
        if css[pos] == '{':
            depth += 1
        elif css[pos] == '}':
            depth -= 1
            if depth == 0:
                return css[start:pos + 1]
    raise AssertionError('unterminated mobile-order media block')


def _orders(block, selector_fn):
    found = {}
    for m in re.finditer(r'([^{}]+)\{\s*order\s*:\s*(\d+)', block):
        sel = m.group(1).strip()
        key = selector_fn(sel)
        if key is not None:
            found[key] = int(m.group(2))
    return found


def _section_key(sel):
    m = re.search(r'#section-([a-z]+)', sel)
    return m.group(1) if m and '.gp-app-main' in sel else None


def _nav_key(sel):
    m = re.search(r'\[data-nav="([a-z]+)"\]', sel)
    return m.group(1) if m and '.gp-bottom-nav' in sel else None


def test_mobile_sections_lead_in_order():
    orders = _orders(_mobile_block(_layout_css()), _section_key)
    assert [orders[n] for n in LEAD] == [1, 2, 3, 4], orders
    assert orders['dashboard'] < orders['conflicts'] < orders['map'] < orders['intelweb']


def test_mobile_bottom_nav_sequence_matches():
    orders = _orders(_mobile_block(_layout_css()), _nav_key)
    assert [orders[n] for n in LEAD] == [1, 2, 3, 4], orders


def test_no_desktop_order_rules():
    css = _layout_css()
    block = _mobile_block(css)
    outside = css.replace(block, '')
    outside = re.sub(r'@media[^{]*\{', '', outside)
    for n in LEAD:
        assert not re.search(r'#section-' + n + r'[^}]*order\s*:', outside), f'desktop order leak: {n}'
        assert not re.search(r'\[data-nav="' + n + r'"\][^}]*order\s*:', outside), f'desktop nav order leak: {n}'


def test_ids_and_nav_hooks_stable():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    for n in LEAD:
        assert f'id="section-{n}"' in html, f'missing section: {n}'
        assert f'data-nav="{n}"' in html, f'missing nav hook: {n}'
