/* Track A GUI-1 Command Center. Vanilla JS. Fetches data/gui-fixtures.json only. No live pipeline. */
(function () {
  'use strict';
  var FIXTURE_URL = 'data/gui-fixtures.json';
  var REFRESH_SEC = 5 * 60;
  var bootTime = Date.now();
  var remaining = REFRESH_SEC;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function num(v, d) {
    var n = Number(v);
    if (!isFinite(n)) return (d == null ? '—' : d);
    return n.toLocaleString('en-US');
  }
  function sevFor(score) {
    var n = Number(score);
    if (!isFinite(n)) return 'info';
    if (n >= 60) return 'critical';
    if (n >= 35) return 'watch';
    if (n >= 20) return 'info';
    return 'healthy';
  }
  function q(root, sel) { return root.querySelector('[data-ta="' + sel + '"]'); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function tickClock(el) {
    if (!el) return;
    var d = new Date();
    el.textContent = pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ':' + pad(d.getUTCSeconds()) + ' UTC';
  }
  function tickCountdown(el) {
    if (!el) return;
    remaining -= 1;
    if (remaining < 0) remaining = REFRESH_SEC;
    var m = Math.floor(remaining / 60), s = remaining % 60;
    el.textContent = pad(m) + ':' + pad(s);
  }
  function tickUptime(el) {
    if (!el) return;
    var s = Math.floor((Date.now() - bootTime) / 1000);
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    el.textContent = pad(h) + ':' + pad(m) + ':' + pad(s % 60);
  }

  function renderReadiness(root, f) {
    var el = q(root, 'readiness');
    if (!el) return;
    var src = f.sources || {};
    var total = Number(src.total_failoverState) || 64;
    function pct(a, b) {
      a = Number(a); b = Number(b);
      if (!isFinite(a) || !isFinite(b) || b <= 0) return 0;
      return Math.max(0, Math.min(100, Math.round(a / b * 1000) / 10));
    }
    var items = [
      ['Power Systems', Number(src.dataCoveragePercent) || 0],
      ['Food Supply', pct(src.healthy, total)],
      ['Connectivity', pct(src.online, total)],
      ['Financial Shields', pct(src.onlineWithData, total)]
    ];
    var html = '';
    for (var i = 0; i < items.length; i++) {
      var v = Math.max(0, Math.min(100, Number(items[i][1]) || 0));
      html += '<div class="ta-ready" role="listitem" tabindex="0" aria-label="' + esc(items[i][0]) + ' ' + v + ' percent">'
        + '<div class="t">' + esc(items[i][0]) + ' <span class="ta-mono">' + v + '%</span></div>'
        + '<div class="ta-bar" role="progressbar" aria-valuenow="' + v + '" aria-valuemin="0" aria-valuemax="100" aria-label="' + esc(items[i][0]) + '">'
        + '<span class="ta-bar-fill" style="width:' + v + '%"></span></div></div>';
    }
    el.innerHTML = html;
  }

  function renderThreats(root, f) {
    var el = q(root, 'threats');
    if (!el) return;
    var bd = (f.tension && f.tension.breakdown) || {};
    var keys = Object.keys(bd).sort(function (a, b) { return Number(bd[b]) - Number(bd[a]); }).slice(0, 3);
    var top = (f.alerts && f.alerts.topConflict) || {};
    var html = '';
    for (var i = 0; i < keys.length; i++) {
      var sc = Number(bd[keys[i]]);
      var sev = sevFor(sc);
      html += '<div class="ta-threat" tabindex="0" aria-label="' + esc(keys[i]) + ' ' + sc + ' percent ' + sev + '">'
        + '<div class="tt">' + esc(keys[i]) + '</div>'
        + '<span class="ta-badge ta-sev-' + sev + '">' + esc(String(Math.round(sc))) + '%</span> '
        + '<span class="ta-badge ta-sev-' + sev + '">' + sev.toUpperCase() + '</span></div>';
    }
    if (top && top.name) {
      html += '<div class="ta-threat" tabindex="0" aria-label="Top conflict ' + esc(top.name) + '">'
        + '<div class="tt">' + esc(top.name) + '</div>'
        + '<span class="ta-badge ta-sev-critical">' + esc(top.escalation || 'CRITICAL') + '</span> '
        + '<span class="ta-sub">' + esc(String(top.signals == null ? '' : top.signals + ' signals')) + '</span></div>';
    }
    var sub = q(root, 'threatsub');
    if (sub) sub.textContent = '· top drivers + top conflict';
    el.innerHTML = html || '<div class="ta-empty">No threats in fixtures.</div>';
  }

  function renderTension(root, f) {
    var t = f.tension || {};
    var eT = q(root, 'tension');
    var eL = q(root, 'tlevel');
    var eD = q(root, 'tdelta');
    var idx = Number(t.index);
    if (eT) eT.textContent = isFinite(idx) ? String(Math.round(idx)) : '—';
    var lvl = ((t.earlyWarning && t.earlyWarning.level) || 'WATCH').toUpperCase();
    if (eL) { eL.textContent = lvl; eL.className = 'ta-badge ta-sev-' + (lvl === 'CRITICAL' ? 'critical' : lvl === 'WATCH' ? 'watch' : lvl === 'STABLE' || lvl === 'OK' ? 'healthy' : 'info'); }
    if (eD) {
      var d = Number(t.delta);
      eD.textContent = isFinite(d) ? ('Δ ' + (d > 0 ? '+' : '') + d) : '';
    }
    var box = q(root, 'drivers');
    if (!box) return;
    var bd = t.breakdown || {};
    var keys = Object.keys(bd);
    if (!keys.length) { box.innerHTML = '<div class="ta-empty">No tension drivers in fixtures.</div>'; return; }
    var html = '';
    keys.sort(function (a, b) { return Number(bd[b]) - Number(bd[a]); });
    for (var i = 0; i < keys.length; i++) {
      var v = Math.max(0, Math.min(100, Number(bd[keys[i]]) || 0));
      html += '<div class="ta-driver"><span>' + esc(keys[i]) + '</span>'
        + '<span class="ta-bar" role="progressbar" aria-valuenow="' + Math.round(v) + '" aria-valuemin="0" aria-valuemax="100" aria-label="' + esc(keys[i]) + '">'
        + '<span class="ta-bar-fill" style="width:' + v + '%"></span></span>'
        + '<span class="ta-mono"><b>' + Math.round(v) + '</b></span></div>';
    }
    box.innerHTML = html;
  }

  function renderSignals(root, f) {
    var el = q(root, 'signals');
    if (!el) return;
    var s = f.signals || {};
    var tiles = [
      [s.stories, 'Stories'],
      [s.liveEvents, 'Live events'],
      [s.conflicts, 'Conflicts'],
      [s.markers, 'Markers']
    ];
    var html = '';
    for (var i = 0; i < tiles.length; i++) {
      html += '<div class="ta-tile" role="listitem" tabindex="0" aria-label="' + esc(tiles[i][1]) + ': ' + esc(String(tiles[i][0])) + '">'
        + '<div class="v ta-mono">' + esc(num(tiles[i][0])) + '</div><div class="l">' + esc(tiles[i][1]) + '</div></div>';
    }
    el.innerHTML = html;
  }

  function hoursSince(iso, fallbackH) {
    var t = Date.parse(iso);
    if (!isFinite(t)) return fallbackH;
    var h = (Date.now() - t) / 3600000;
    if (h < 0) return 0;
    return Math.round(h * 10) / 10;
  }

  function renderFresh(root, f) {
    var el = q(root, 'fresh');
    if (!el) return;
    var frozen = (f.meta && f.meta.frozenAt) || null;
    var mk = (f.market && f.market.updatedAt) || null;
    var tiles = [
      ['Snapshot', hoursSince(frozen, 20)],
      ['Market', hoursSince(mk, 45)],
      ['Breaking window', '0.25'],
      ['Sources', hoursSince(frozen, 20)],
      ['Events', hoursSince(frozen, 20)],
      ['Brief', hoursSince(frozen, 20)]
    ];
    var html = '';
    for (var i = 0; i < tiles.length; i++) {
      html += '<div class="ta-tile" tabindex="0" aria-label="' + esc(tiles[i][0]) + ' freshness ' + esc(String(tiles[i][1])) + ' hours">'
        + '<div class="v ta-mono">' + esc(String(tiles[i][1])) + 'h</div><div class="l">' + esc(tiles[i][0]) + '</div></div>';
    }
    el.innerHTML = html;
  }

  function renderMarket(root, f) {
    var m = f.market || {};
    var box = q(root, 'market');
    if (!box) return;
    var n = Number(m.indicators);
    var note = String(m.note || 'Yahoo Finance 1m');
    box.innerHTML = '<span class="ta-badge ta-sev-info">DELAYED</span>'
      + '<span><b class="ta-mono">' + esc(isFinite(n) ? String(n) : '—') + '</b> indicators</span>'
      + '<span class="ta-sub">' + esc(note) + '</span>'
      + (m.updatedAt ? '<span class="ta-sub ta-mono">' + esc(String(m.updatedAt).slice(0, 16).replace('T', ' ')) + '</span>' : '');
  }

  function renderHead(root, f) {
    var op = q(root, 'opstate');
    var src = q(root, 'src');
    var tasks = q(root, 'tasks');
    var s = f.sources || {};
    var healthy = Number(s.healthy), total = Number(s.total_failoverState) || 64;
    if (src) src.textContent = (isFinite(healthy) ? healthy : '—') + '/' + total + ' sources';
    if (tasks) tasks.textContent = (isFinite(Number(s.online)) ? s.online : '—') + ' active';
    if (op) {
      var ok = isFinite(healthy) && healthy >= 50;
      op.textContent = ok ? 'OPERATIONAL' : 'DEGRADED';
    }
  }

  function renderAll(root, data) {
    var empty = q(root, 'empty');
    if (!data || typeof data !== 'object') {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    renderHead(root, data);
    renderReadiness(root, data);
    renderThreats(root, data);
    renderTension(root, data);
    renderSignals(root, data);
    renderFresh(root, data);
    renderMarket(root, data);
  }

  function fetchFixtures() {
    return fetch(FIXTURE_URL, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function initCenter(rootId) {
    var root = document.getElementById(rootId || 'trackA-center');
    if (!root) return false;
    if (root.getAttribute('data-ta-init') === '1') return true;
    root.setAttribute('data-ta-init', '1');
    var cClock = q(root, 'clock'), cDown = q(root, 'countdown'), cUp = q(root, 'uptime');
    tickClock(cClock); tickUptime(cUp);
    if (cDown) cDown.textContent = '05:00';
    var reduce = false;
    try { reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
    setInterval(function () { tickClock(cClock); tickUptime(cUp); if (!reduce) tickCountdown(cDown); }, 1000);
    fetchFixtures().then(function (d) { renderAll(root, d); remaining = REFRESH_SEC; })
      .catch(function () { var e = q(root, 'empty'); if (e) e.hidden = false; });
    return true;
  }

  if (typeof window !== 'undefined') {
    window.TrackACenter = { init: initCenter };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { initCenter('trackA-center'); });
    } else {
      initCenter('trackA-center');
    }
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { init: initCenter };
})();
