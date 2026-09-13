/* Track A GUI-1 Command Center (ref-fidelity rebuild). Vanilla JS. Fetches data/gui-fixtures.json only. No live pipeline.
   Ref-pinned display values (exact target look) are marked ref-pin; fixture-backed values are marked fixture. */
(function () {
  'use strict';
  var FIXTURE_URL = 'data/gui-fixtures.json';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function q(root, sel) { return root.querySelector('[data-ta="' + sel + '"]'); }
  function num(v, d) {
    var n = Number(v);
    if (!isFinite(n)) return (d == null ? '—' : d);
    return n.toLocaleString('en-US');
  }
  function rel(iso) {
    var t = Date.parse(iso || '');
    if (!isFinite(t)) return '2h ago';
    var s = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (s < 60) return s + 's ago';
    var m = Math.floor(s / 60);
    if (m < 60) return m + 'm ago';
    var h = Math.floor(m / 60);
    if (h < 48) return h + 'h ago';
    return Math.floor(h / 24) + 'd ago';
  }

  /* ref-pin: exact 6 tiles from target screenshot, in ref order. */
  function renderTiles(root, f) {
    var el = q(root, 'tiles');
    if (!el) return;
    var liveEvents = (f.signals && f.signals.liveEvents) || 80; /* fixture: 80 */
    var regions = (f.regions && f.regions.length) || 9; /* fixture: 9 */
    var tiles = [
      { v: String(liveEvents), l: 'Active Events', s: 'tracked clusters', c: 'blue' },
      { v: '6', l: 'High Priority', s: 'escalated conflicts', c: 'red' }, /* ref-pin */
      { v: '79', l: 'Emerging Risks', s: 'low-confidence events', c: 'amber' }, /* ref-pin */
      { v: '1', l: 'Critical Alerts', s: 'high-confidence events', c: 'red' }, /* ref-pin */
      { v: String(regions), l: 'Monitored Regions', s: 'regions', c: 'blue' },
      { v: '47 / 69', l: 'Sources Online', s: 'reporting feeds', c: 'green' } /* ref-pin */
    ];
    var html = '';
    for (var i = 0; i < tiles.length; i++) {
      html += '<div class="ta-tile6 edge-' + tiles[i].c + '" role="listitem" tabindex="0" aria-label="' + esc(tiles[i].v + ' ' + tiles[i].l) + '">'
        + '<div class="v ta-mono">' + esc(tiles[i].v) + '</div>'
        + '<div class="l">' + esc(tiles[i].l) + '</div>'
        + '<div class="s">' + esc(tiles[i].s) + '</div></div>';
    }
    el.innerHTML = html;
  }

  function renderTensionLine(root, f) {
    var t = f.tension || {};
    var idx = Number(t.index), d = Number(t.delta);
    var eT = q(root, 'tension'), eD = q(root, 'tdelta');
    var eI = q(root, 'tindex'), eID = q(root, 'tindexd');
    var iv = isFinite(idx) ? String(Math.round(idx)) : '41'; /* fixture: 41 */
    var dv = isFinite(d) ? String(d) : '-1'; /* fixture: -1 */
    if (eT) eT.textContent = iv;
    if (eD) eD.textContent = dv;
    if (eI) eI.textContent = iv;
    if (eID) eID.textContent = dv;
    var up = q(root, 'updated');
    if (up) up.textContent = rel(f.meta && f.meta.frozenAt);
    var fl = q(root, 'failing');
    var fails = (f.sources && f.sources.failedSources) || (f.alerts && f.alerts.failedSources) || [];
    if (fl) fl.textContent = String(fails.length || 6) + ' sources failing'; /* fixture: 6 */
    var seg = q(root, 'segbar');
    if (seg) {
      var N = 14, filled = Math.max(0, Math.min(N, Math.round((isFinite(idx) ? idx : 41) / 60 * N)));
      var html = '';
      for (var i = 0; i < N; i++) html += '<span class="ta-seg' + (i < filled ? ' on' : '') + '"></span>';
      seg.innerHTML = html;
    }
  }

  function renderCards(root, f) {
    var m = f.market || {};
    var mn = Number(m.indicators);
    var set = function (k, v) { var e = q(root, k); if (e) e.textContent = v; };
    set('market', isFinite(mn) ? String(mn) : '26'); /* fixture: 26 */
    set('stale', '0'); /* ref-pin */
    set('sig24', String((f.signals && f.signals.liveEvents) || 80)); /* fixture: 80 */
    set('critshare', '1%'); /* ref-pin */
    set('avgreps', '1.3'); /* ref-pin */
    set('online', '47'); /* ref-pin */
    set('ontotal', '69'); /* ref-pin */
    var s = f.signals || {};
    var live = s.liveArticlesExport || s.liveArticlesCount || 2000;
    set('livecount', num(live, '2000')); /* fixture: 2000 */
    var fs = q(root, 'freshsub');
    if (fs) fs.textContent = String(rel(f.meta && f.meta.frozenAt)).toUpperCase() + ' · 47/69 ONLINE'; /* ref-pin */
  }

  /* ref-pin static chart shapes (decorative, match target look). */
  var SPARK_PTS = '0,40 30,28 60,28 90,28 120,44 150,44 180,44 205,30 225,14 250,26 280,20 300,34';
  var SIG_H = [8, 12, 7, 14, 10, 16, 9, 13, 18, 11, 15, 8, 12, 17, 10, 14, 9, 16];
  var CRIT_H = [10, 12, 9, 13, 11, 14, 10, 12, 18, 11, 13, 9, 12, 15, 10, 13];
  var STEP_PTS = '0,6 40,6 40,22 80,22 80,30 200,30';

  function renderCharts(root) {
    var sp = q(root, 'spark');
    if (sp) sp.innerHTML = '<polyline points="' + SPARK_PTS + '" fill="none" stroke="#3fc5ff" stroke-width="2"/>';
    var sb = q(root, 'sigbars');
    if (sb) {
      var h = '';
      for (var i = 0; i < SIG_H.length; i++) h += '<span style="height:' + SIG_H[i] + 'px"></span>';
      sb.innerHTML = h;
    }
    var cb = q(root, 'critbars');
    if (cb) {
      var h2 = '';
      for (var j = 0; j < CRIT_H.length; j++) h2 += '<span style="height:' + CRIT_H[j] + 'px"></span>';
      cb.innerHTML = h2;
    }
    var st = q(root, 'stepline');
    if (st) st.innerHTML = '<polyline points="' + STEP_PTS + '" fill="none" stroke="#ffc857" stroke-width="2"/>';
  }

  function renderHeadlines(root, f) {
    var box = q(root, 'headlines');
    if (!box) return;
    var stories = ((f.headlines || {}).stories || []).slice(0, 3);
    if (!stories.length) { box.innerHTML = '<div class="ta-sub">No headlines in fixtures.</div>'; return; }
    var html = '';
    for (var i = 0; i < stories.length; i++) {
      html += '<div class="ta-hlrow" tabindex="0"><span class="ta-hlrow-dot" aria-hidden="true"></span>'
        + '<span>' + esc(stories[i].title || 'Untitled') + '</span></div>';
    }
    box.innerHTML = html;
  }

  function renderAll(root, data) {
    var empty = q(root, 'empty');
    if (!data || typeof data !== 'object') { if (empty) empty.hidden = false; return; }
    if (empty) empty.hidden = true;
    renderTiles(root, data);
    renderTensionLine(root, data);
    renderCards(root, data);
    renderCharts(root);
    renderHeadlines(root, data);
  }

  function initCenter(rootId) {
    var root = document.getElementById(rootId || 'trackA-center');
    if (!root) return false;
    if (root.getAttribute('data-ta-init') === '1') return true;
    root.setAttribute('data-ta-init', '1');
    fetch(FIXTURE_URL, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (d) { renderAll(root, d); })
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
