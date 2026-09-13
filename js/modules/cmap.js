/* Track A GUI-4 Global Map. Vanilla JS. Fetches data/gui-fixtures.json only. */
(function () {
  'use strict';
  var FIXTURE_URL = 'data/gui-fixtures.json';
  var currentRange = '24H';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function tm(root, sel) { return root.querySelector('[data-tm="' + sel + '"]'); }
  function sevFor(score) {
    var n = Number(score);
    if (!isFinite(n)) return 'info';
    if (n >= 60) return 'critical';
    if (n >= 20) return 'watch';
    return 'stable';
  }
  function scoreOf(r) {
    var rep = Number(r.reports) || 0, ev = Number(r.events) || 0;
    if (currentRange === '24H') return ev * 5 + Math.min(rep, 20);
    if (currentRange === '7D') return rep + ev * 2;
    return rep + ev * 3;
  }

  function renderChips(root, regions) {
    var box = tm(root, 'chips');
    if (!box) return;
    if (!regions || !regions.length) { box.innerHTML = '<div class="ta-empty">No regions in fixtures.</div>'; return; }
    var sorted = regions.slice().sort(function (a, b) { return scoreOf(b) - scoreOf(a); });
    var html = '';
    for (var i = 0; i < sorted.length; i++) {
      var sc = scoreOf(sorted[i]);
      html += '<span class="ta-chip" tabindex="0" aria-label="' + esc(sorted[i].name) + ' score ' + sc + '">'
        + esc(String(sorted[i].name).toUpperCase()) + ' ' + '<span class="ta-mono">' + sc + '</span></span>';
    }
    box.innerHTML = html;
  }

  function renderTable(root, regions) {
    var body = tm(root, 'pbody');
    if (!body) return;
    if (!regions || !regions.length) { body.innerHTML = '<tr><td colspan="4">No regions.</td></tr>'; return; }
    var sorted = regions.slice().sort(function (a, b) { return scoreOf(b) - scoreOf(a); });
    var html = '';
    for (var i = 0; i < sorted.length; i++) {
      var sc = scoreOf(sorted[i]);
      var sev = sevFor(sc);
      var ev = Number(sorted[i].events) || 0;
      html += '<tr><td>' + esc(sorted[i].name) + '</td>'
        + '<td class="ta-mono"><b>' + sc + '</b></td>'
        + '<td><span class="ta-badge ta-sev-' + sev + '">' + sev.toUpperCase() + '</span></td>'
        + '<td class="ta-mono">' + ev + '</td></tr>';
    }
    body.innerHTML = html;
  }

  function renderTiles(root, f) {
    var c = tm(root, 'conflicts'), r = tm(root, 'regions');
    var s = f.signals || {};
    if (c) c.textContent = String(s.conflicts == null ? '—' : Number(s.conflicts).toLocaleString('en-US'));
    var regs = f.regions || [];
    if (r) r.textContent = String(regs.length || 0);
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
      [dArrow, 'Tension ' + (t.index == null ? '—' : t.index) + ' (' + (isFinite(d) ? (d > 0 ? '+' : '') + d : '—') + ' / 24H)'],
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
    renderChanged(root, data);
    var range = tm(root, 'range');
    if (range) range.textContent = currentRange;
  }

  function setupPills(root, data) {
    var box = tm(root, 'pills');
    if (!box) return;
    var btns = box.querySelectorAll('button[data-range]');
    function select(btn) {
      currentRange = btn.getAttribute('data-range') || '24H';
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
      if (b) b.innerHTML = '<tr><td colspan="4">Map data unavailable.</td></tr>';
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
