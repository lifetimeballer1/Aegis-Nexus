"""Hotfix alerts-js — shipped-JS syntax regression gate.

P0: Phase 1 shipped js/modules/briefings.js:122 with a swapped paren/brace
(`${esc(dev.id || dev.title || ''})}` — the `}` closed the `${` while `esc(`
was still open). alerts.js statically imports briefings.js, so the whole
Alerts tab rendered "Temporarily unavailable. Unexpected token '}'...".

A whole-file brace/paren counter would NOT have caught this (totals still
balance); only an order-sensitive stack check does. This test embeds a
node-free stack validator (the burst box has no JS runtime) that tracks
`()[]{}` + template-literal `${}` nesting with string/comment awareness,
and runs it over every shipped js/ file. Verified: fails on the pre-fix
briefings.js (`'}' closes '(' opened at line 122`), passes on the fixed tree
in agreement with `node --check`.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_js_nesting(src, name='<src>'):
    """Return list of error strings; empty means OK. Stack-based: catches
    misordered closers (e.g. `}` closing `${` while `(` is still open) that
    naive balance counters miss."""
    errors = []
    stack = []          # '(' '[' '{' or '${' (+ source line)
    i, n = 0, len(src)
    line = 1
    in_line_comment = False
    in_block_comment = False
    in_str = None
    in_tpl = False
    tpl_stack = []
    prev_sig = None

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if c == '\n':
            line += 1
            in_line_comment = False
            i += 1
            continue
        if in_line_comment:
            i += 1
            continue
        if in_block_comment:
            if c == '*' and nxt == '/':
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == in_str:
                in_str = None
                prev_sig = 's'
            i += 1
            continue
        if in_tpl:
            if c == '\\':
                i += 2
                continue
            if c == '`':
                in_tpl = False
                tpl_stack.pop()
                prev_sig = 's'
                i += 1
                continue
            if c == '$' and nxt == '{':
                stack.append(('${', line))
                in_tpl = False
                prev_sig = '{'
                i += 2
                continue
            i += 1
            continue
        if c == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            continue
        if c == '/' and nxt == '*':
            in_block_comment = True
            i += 2
            continue
        if c in '\'"':
            in_str = c
            i += 1
            continue
        if c == '`':
            in_tpl = True
            tpl_stack.append(line)
            i += 1
            continue
        if c == '/' and nxt not in ('/', '*'):
            if prev_sig is None or prev_sig in '([{=,:;!&|?+-*%^~<>':
                j = i + 1
                in_class = False
                closed = False
                while j < n:
                    ch = src[j]
                    if ch == '\n':
                        break
                    if ch == '\\':
                        j += 2
                        continue
                    if ch == '[':
                        in_class = True
                    elif ch == ']':
                        in_class = False
                    elif ch == '/' and not in_class:
                        closed = True
                        break
                    j += 1
                if closed:
                    j += 1
                    while j < n and src[j] in 'dgimsuvy':
                        j += 1
                    i = j
                    prev_sig = 's'
                    continue
            i += 1
            continue
        if c in '([{':
            stack.append((c, line))
            prev_sig = c
            i += 1
            continue
        if c in ')]}':
            match = {')': '(', ']': '[', '}': '{'}[c]
            if c == '}' and stack and stack[-1][0] == '${':
                stack.pop()
                in_tpl = True
                prev_sig = 's'
                i += 1
                continue
            if not stack:
                errors.append('%s:%d: unmatched %r' % (name, line, c))
                i += 1
                continue
            top, top_line = stack[-1]
            if top == '${' or top != match:
                errors.append('%s:%d: %r closes %r opened at line %d'
                              % (name, line, c, top, top_line))
                i += 1
                continue
            stack.pop()
            prev_sig = c
            i += 1
            continue
        if not c.isspace():
            prev_sig = c if not (c.isalnum() or c in '_$') else 'w'
        i += 1

    if in_tpl or tpl_stack:
        errors.append('%s:%d: unterminated template literal' % (name, line))
    if in_str:
        errors.append('%s:%d: unterminated string' % (name, line))
    if in_block_comment:
        errors.append('%s:%d: unterminated block comment' % (name, line))
    for tok, tok_line in stack:
        errors.append('%s:%d: unclosed %r' % (name, tok_line, tok))
    return errors


def _shipped_js():
    return sorted((ROOT / 'js').rglob('*.js'))


def test_shipped_js_files_exist():
    files = _shipped_js()
    assert len(files) > 10, 'expected a tree of shipped JS under js/'


def test_shipped_js_nesting_balanced():
    """Order-sensitive bracket/template check over every shipped JS file."""
    failures = []
    for path in _shipped_js():
        errs = check_js_nesting(path.read_text(encoding='utf-8'), str(path))
        failures.extend(errs)
    assert not failures, 'JS nesting errors:\n' + '\n'.join(failures)


def test_briefings_template_paren_order():
    """The exact P0 pattern: `${esc(... || ''})}` must never ship again."""
    js = (ROOT / 'js/modules/briefings.js').read_text(encoding='utf-8')
    assert "|| ''})}" not in js, 'swapped paren/brace template placeholder is back'
    assert "${esc(dev.id || dev.title || '')}" in js


def test_briefings_drawer_html_is_appended():
    """briefDrawerHtml() must be part of the innerHTML chain, not a discarded
    `+ expr;` statement after a semicolon (a second Phase-1 defect in the
    same function that silently dropped the brief detail drawer)."""
    js = (ROOT / 'js/modules/briefings.js').read_text(encoding='utf-8')
    assert 'briefDrawerHtml(developments)' in js
    bad = ": '');\n    + briefDrawerHtml(developments);"
    assert bad not in js, 'drawer HTML is a discarded expression statement again'


def test_stat_tile_labels_wrap_at_word_boundaries():
    """390px stat tiles: 2-up so labels fit; breaks only at word boundaries."""
    css = (ROOT / 'css/track-a.css').read_text(encoding='utf-8')
    assert 'overflow-wrap:break-word' in css
    assert '.ta-tiles6{grid-template-columns:repeat(2,minmax(0,1fr))}' in css
    dash = (ROOT / 'css/dashboard.css').read_text(encoding='utf-8')
    assert '.cc-kpi .l{word-break:normal;overflow-wrap:break-word;hyphens:none}' in dash


def test_bottom_bar_clock_spacing():
    """Bottom-bar clock copies #commandClock spans with no flex gap; the
    date/UTC pair needs its own margin ("Sep 1415:58 UTC" regression)."""
    css = (ROOT / 'css/command-shell.css').read_text(encoding='utf-8')
    assert '#commandStatusBarClock .cs-utc{margin-left:' in css
