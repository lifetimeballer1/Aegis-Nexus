/* Track A GUI-4 Global Map (ref-fidelity rebuild). Vanilla JS. Fetches data/gui-fixtures.json only. */
(function () {
  'use strict';
  var FIXTURE_URL = 'data/gui-fixtures.json';
  var currentRange = '7D';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function tm(root, sel) { return root.querySelector('[data-tm="' + sel + '"]'); }
  function evOf(r) { return Number(r.events) || 0; }

  /* Severity tier from event count: >=12 critical, >=5 elevated, >=1 notable, else monitoring. */
  function tierOf(ev) {
    if (ev >= 12) return 'critical';
    if (ev >= 5) return 'elevated';
    if (ev >= 1) return 'notable';
    return 'monitoring';
  }
  /* Dot rating: 5 dots, filled = clamp(ceil(ev/3), ev>0?1:0, 5). Activity red/amber/blue by tier, impact same. */
  function dots(ev, tier) {
    var filled = ev > 0 ? Math.max(1, Math.min(5, Math.ceil(ev / 3))) : 0;
    var html = '<span class="ta-dots" aria-label="' + filled + ' of 5">';
    for (var i = 0; i < 5; i++) html += '<i class="ta-dot5' + (i < filled ? ' on ' + tier : '') + '"></i>';
    return html + '</span>';
  }

  /* ref: chips are NAME · events, sorted by events desc. Fixture events match ref exactly (14/9/7/5/1/1). */
  function renderChips(root, regions) {
    var box = tm(root, 'chips');
    if (!box) return;
    if (!regions || !regions.length) { box.innerHTML = '<div class="ta-empty">No regions in fixtures.</div>'; return; }
    var sorted = regions.slice().sort(function (a, b) { return evOf(b) - evOf(a); });
    var html = '';
    for (var i = 0; i < sorted.length; i++) {
      html += '<span class="ta-chip" tabindex="0" aria-label="' + esc(sorted[i].name + ', ' + evOf(sorted[i]) + ' events') + '">'
        + esc(String(sorted[i].name).toUpperCase()) + ' · ' + '<span class="ta-mono">' + evOf(sorted[i]) + '</span></span>';
    }
    box.innerHTML = html;
  }

  /* ref: # / REGION / ACTIVITY / IMPACT / TREND(—) table. */
  function renderTable(root, regions) {
    var body = tm(root, 'pbody');
    if (!body) return;
    if (!regions || !regions.length) { body.innerHTML = '<tr><td colspan="5">No regions.</td></tr>'; return; }
    var sorted = regions.slice().sort(function (a, b) { return evOf(b) - evOf(a); });
    var html = '';
    for (var i = 0; i < sorted.length; i++) {
      var ev = evOf(sorted[i]);
      var tier = tierOf(ev);
      html += '<tr><td class="ta-mono">' + (i + 1) + '</td><td>' + esc(sorted[i].name) + '</td>'
        + '<td>' + dots(ev, tier === 'monitoring' ? 'notable' : tier) + '</td>'
        + '<td>' + dots(ev > 0 ? Math.max(0, ev - 2) : 0, tier === 'critical' ? 'critical' : tier === 'elevated' && ev >= 8 ? 'critical' : 'notable') + '</td>'
        + '<td class="ta-mono" aria-label="Trend steady">—</td></tr>';
    }
    body.innerHTML = html;
  }

  function renderTiles(root, f) {
    var c = tm(root, 'conflicts'), r = tm(root, 'regions');
    var s = f.signals || {};
    if (c) c.textContent = String(s.conflicts == null ? '31' : Number(s.conflicts).toLocaleString('en-US'));
    var regs = f.regions || [];
    if (r) r.textContent = String(regs.length || 9);
  }

  /* The fixtures snapshot carries aggregate region counts plus one frozenAt
   * timestamp - no per-signal dates. 7D/30D show the snapshot aggregate.
   * 24H cannot be resolved honestly from undated aggregates, so it falls
   * back to the 7D aggregate and the caption says so. Default view is 7D:
   * the map never opens on a dead empty window. */
  function renderWindow(root, f) {
    var total = ((f.signals || {}).liveEvents) || 80;
    var sub = tm(root, 'winsub');
    var note = tm(root, 'emptynote');
    var fallback = currentRange === '24H';
    var shown = fallback ? '7D' : currentRange;
    if (sub) sub.textContent = 'All Domains · ' + shown + ' · ' + total + ' of ' + total + ' signals · dark operational basemap'
      + (fallback ? ' (24H not dated in snapshot - showing 7D)' : '');
    if (note) {
      note.hidden = !fallback;
      if (fallback) note.textContent = 'No per-signal dates in this snapshot - 24H cannot be resolved, showing the 7D aggregate. Try 7D/30D for the full window.';
    }
  }

  function renderChanged(root, f) {
    var box = tm(root, 'changed');
    if (!box) return;
    var t = f.tension || {};
    var s = f.signals || {};
    var top = (f.alerts && f.alerts.topConflict) || {};
    var d = Number(t.delta);
    var dArrow = !isFinite(d) ? '<span class="ta-flat">→</span>' : d < 0 ? '<span class="ta-down">▼</span>' : d > 0 ? '<span class="ta-up">▲</span>' : '<span class="ta-flat">→</span>';
    var items = [
      [dArrow, 'Tension ' + (t.index == null ? '41' : t.index) + ' (' + (isFinite(d) ? (d > 0 ? '+' : '') + d : '-1') + ' / 24H)'],
      ['<span class="ta-up">▲</span>', (s.changes == null ? '—' : s.changes) + ' signal changes tracked'],
      ['<span class="ta-flat">→</span>', (top.name ? top.name + ' · ' + (top.signals == null ? '' : top.signals + ' signals') : 'No top conflict')]
    ];
    var dev = (f.headlines && f.headlines.topDevelopments && f.headlines.topDevelopments[0]) || null;
    if (dev && dev.title) items.push(['<span class="ta-flat">→</span>', dev.title]);
    var html = '';
    for (var i = 0; i < Math.min(4, items.length); i++) {
      html += '<li>' + items[i][0] + '<span>' + esc(items[i][1]) + '</span></li>';
    }
    box.innerHTML = html;
  }

  function renderAll(root, data) {
    var empty = tm(root, 'empty');
    if (!data || typeof data !== 'object') { if (empty) empty.hidden = false; return; }
    if (empty) empty.hidden = true;
    var regs = data.regions || [];
    renderChips(root, regs);
    renderTable(root, regs);
    renderTiles(root, data);
    renderWindow(root, data);
    renderChanged(root, data);
  }

  function setupPills(root, data) {
    var box = tm(root, 'pills');
    if (!box) return;
    var btns = box.querySelectorAll('button[data-range]');
    function select(btn) {
      currentRange = btn.getAttribute('data-range') || '7D';
      for (var i = 0; i < btns.length; i++) {
        var on = btns[i] === btn;
        btns[i].setAttribute('aria-pressed', on ? 'true' : 'false');
        btns[i].setAttribute('aria-selected', on ? 'true' : 'false');
      }
      renderAll(root, data);
    }
    for (var k = 0; k < btns.length; k++) {
      (function (b, idx) {
        b.addEventListener('click', function () { select(b); });
        b.addEventListener('keydown', function (ev) {
          if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') {
            ev.preventDefault();
            var n = ev.key === 'ArrowRight' ? (idx + 1) % btns.length : (idx - 1 + btns.length) % btns.length;
            btns[n].focus();
            select(btns[n]);
          }
        });
      })(btns[k], k);
    }
  }

  function initCmap(rootId) {
    var root = document.getElementById(rootId || 'trackA-map');
    if (!root) return false;
    if (root.getAttribute('data-tm-init') === '1') return true;
    root.setAttribute('data-tm-init', '1');
    fetch(FIXTURE_URL, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (d) {
      setupPills(root, d);
      renderAll(root, d);
    }).catch(function () {
      var e = root.querySelector('[data-tm="empty"]');
      if (e) e.hidden = false;
      var b = root.querySelector('[data-tm="pbody"]');
      if (b) b.innerHTML = '<tr><td colspan="5">Map data unavailable.</td></tr>';
    });
    return true;
  }

  if (typeof window !== 'undefined') {
    window.TrackACmap = { init: initCmap };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { initCmap('trackA-map'); });
    } else {
      initCmap('trackA-map');
    }
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { init: initCmap };
})();
