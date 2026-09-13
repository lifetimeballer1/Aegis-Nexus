/* TRACK-D — ALERTS & Priority Feed (builder D).
 * Classic script (matches ccenter.js pattern). Exposes window.Calerts = { init }.
 * Data: fetch('data/gui-fixtures.json') only — no live calls, nothing fabricated.
 * Severity is derived ONLY from pipeline fields: conflict `escalation`,
 * early-warning `level`, development/event `confidence`+`category`, feed outages.
 * Every card carries source attribution. Ages come from meta.frozenAt only. */
(function () {
  'use strict';

  var FIXTURES = 'data/gui-fixtures.json';
  var ROOT_ID = 'alertsBody';
  var MAX_ATTEMPTS = 3;
  var BASE_DELAY_MS = 800;

  var SEV_RANK = { CRITICAL: 0, WATCH: 1, INFO: 2 };
  var FILTERS = ['ALL', 'CRITICAL', 'WATCH', 'INFO'];

  var state = { filter: 'ALL', alerts: [], updatedAt: null, retrying: false, error: null };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* "2h ago" style relative age from an ISO timestamp. Null-safe. */
  function relAge(iso) {
    if (!iso) return 'unknown age';
    var t = Date.parse(iso);
    if (isNaN(t)) return 'unknown age';
    var s = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (s < 60) return 'just now';
    var m = Math.floor(s / 60);
    if (m < 60) return m + 'm ago';
    var h = Math.floor(m / 60);
    if (h < 48) return h + 'h ago';
    return Math.floor(h / 24) + 'd ago';
  }

  function normConf(c) {
    c = String(c || '').toLowerCase();
    if (c === 'high' || c === 'moderate' || c === 'low') return c;
    return 'unverified';
  }

  /* Severity rules (documented, deterministic):
   * - conflict escalation CRITICAL -> CRITICAL
   * - early-warning level maps 1:1 (WATCH/CRITICAL/...)
   * - development/event: confidence high OR category conflict -> WATCH, else INFO
   * - feed outage touching the top conflict's coverage -> WATCH, other outages -> INFO */
  function buildAlerts(d) {
    var out = [];
    var fx = d || {};
    var alerts = fx.alerts || {};
    var headlines = fx.headlines || {};

    if (alerts.topConflict && alerts.topConflict.name) {
      var tc = alerts.topConflict;
      out.push({
        sev: String(tc.escalation || 'WATCH').toUpperCase() === 'CRITICAL' ? 'CRITICAL' : 'WATCH',
        title: tc.name,
        detail: 'Top conflict by signal volume. Escalation: ' + esc(tc.escalation || 'n/a') + '.',
        confidence: 'high',
        counts: [['signals', tc.signals]],
        source: 'Conflict monitor · gui-fixtures alerts.topConflict'
      });
    }

    var ew = alerts.earlyWarning;
    if (ew && (ew.level || ew.score != null)) {
      var score = Number(ew.score);
      out.push({
        sev: String(ew.level || 'WATCH').toUpperCase() === 'CRITICAL' ? 'CRITICAL' : 'WATCH',
        title: 'Early warning: ' + (ew.strongestDriver || 'aggregate pressure') +
          ' driving ' + (ew.direction || 'stable') + ' momentum',
        detail: 'Level ' + esc(ew.level || 'n/a') + ' · score ' + (isNaN(score) ? 'n/a' : score) +
          (ew.strongestDriverScore != null ? ' · strongest driver ' + esc(ew.strongestDriverScore) : '') + '.',
        confidence: !isNaN(score) && score >= 70 ? 'high' : (!isNaN(score) && score >= 40 ? 'moderate' : 'low'),
        counts: [['score', ew.score], ['momentum', ew.momentum]],
        source: 'Early-warning model · gui-fixtures alerts.earlyWarning'
      });
    }

    (headlines.topDevelopments || []).slice(0, 6).forEach(function (dev) {
      if (!dev || !dev.title) return;
      var conf = normConf(dev.confidence);
      var sev = (conf === 'high' || String(dev.category || '').toLowerCase() === 'conflict') ? 'WATCH' : 'INFO';
      out.push({
        sev: sev,
        title: dev.title,
        detail: 'Category: ' + esc(dev.category || 'general') + '.',
        confidence: conf,
        counts: [],
        source: 'Top developments · gui-fixtures headlines.topDevelopments'
      });
    });

    (headlines.events || []).slice(0, 6).forEach(function (ev) {
      if (!ev || !ev.title) return;
      var conf = normConf(ev.confidence);
      var sev = (conf === 'high' || String(ev.category || '').toLowerCase() === 'conflict') ? 'WATCH' : 'INFO';
      out.push({
        sev: sev,
        title: ev.title,
        detail: 'Category: ' + esc(ev.category || 'general') + '.',
        confidence: conf,
        counts: [['reports', ev.reports]],
        source: 'Live events · gui-fixtures headlines.events'
      });
    });

    var failed = alerts.failedSources || [];
    var cartel = failed.filter(function (f) { return /cartel|gdelt/i.test(f); });
    var rest = failed.filter(function (f) { return !/cartel|gdelt/i.test(f); });
    cartel.forEach(function (f) {
      out.push({
        sev: 'WATCH',
        title: 'Feed degraded: ' + f,
        detail: 'Collector failing inside the ' + (alerts.breakingWindow || '15min') +
          ' breaking window; top-conflict coverage may be stale.',
        confidence: 'moderate',
        counts: [],
        source: 'Source health monitor · gui-fixtures alerts.failedSources'
      });
    });
    if (rest.length) {
      out.push({
        sev: 'INFO',
        title: rest.length + ' auxiliary feeds failing (' + rest.slice(0, 3).join(', ') +
          (rest.length > 3 ? ', …' : '') + ')',
        detail: 'Non-critical collectors erroring; core signal flow unaffected.',
        confidence: 'low',
        counts: [['failing', rest.length]],
        source: 'Source health monitor · gui-fixtures alerts.failedSources'
      });
    }

    out.sort(function (a, b) {
      var r = (SEV_RANK[a.sev] != null ? SEV_RANK[a.sev] : 9) -
              (SEV_RANK[b.sev] != null ? SEV_RANK[b.sev] : 9);
      if (r !== 0) return r;
      return (sigCount(b) - sigCount(a));
    });
    return out;
  }

  function sigCount(a) {
    var n = 0;
    (a.counts || []).forEach(function (c) {
      var v = Number(c[1]);
      if (!isNaN(v)) n += v;
    });
    return n;
  }

  function cardHtml(a, i, age) {
    var sev = a.sev.toLowerCase();
    var counts = (a.counts || []).filter(function (c) { return c[1] != null && c[1] !== ''; })
      .map(function (c) {
        return '<span class="td-count td-mono">' + esc(c[0]) + ': ' + esc(c[1]) + '</span>';
      }).join('');
    return '<article class="td-card td-sev-' + sev + '" role="listitem" data-testid="td-card-' + i + '">' +
      '<div class="td-card-top">' +
        '<span class="td-badge td-badge-' + sev + '">' + esc(a.sev) + '</span>' +
        '<span class="td-conf">Confidence: ' + esc(a.confidence) + '</span>' +
        '<span class="td-age td-mono">' + esc(age) + '</span>' +
      '</div>' +
      '<h3 class="td-title">' + esc(a.title) + '</h3>' +
      '<p class="td-detail">' + a.detail + '</p>' +
      (counts ? '<div class="td-counts">' + counts + '</div>' : '') +
      '<p class="td-src">Source: ' + esc(a.source) + '</p>' +
    '</article>';
  }

  function countsBySev() {
    var c = { ALL: state.alerts.length, CRITICAL: 0, WATCH: 0, INFO: 0 };
    state.alerts.forEach(function (a) { if (c[a.sev] != null) c[a.sev]++; });
    return c;
  }

  function render(root) {
    var q = function (sel) { return root.querySelector(sel); };
    var age = state.updatedAt ? relAge(state.updatedAt) : 'unknown age';
    var upd = q('[data-td="updated"]');
    if (upd) upd.textContent = age;
    var counts = countsBySev();
    root.querySelectorAll('[data-td-filter]').forEach(function (btn) {
      var f = btn.getAttribute('data-td-filter');
      btn.setAttribute('aria-pressed', f === state.filter ? 'true' : 'false');
      var label = f.charAt(0) + f.slice(1).toLowerCase();
      btn.textContent = label + ' (' + (counts[f] || 0) + ')';
    });
    var retry = q('[data-td="retry"]');
    if (retry) {
      retry.disabled = state.retrying;
      retry.textContent = state.retrying ? 'Retrying…' : 'Retry';
    }
    var status = q('[data-td="status"]');
    var list = q('[data-td="list"]');
    if (state.error && !state.alerts.length) {
      if (status) status.textContent = state.error;
      if (list) list.innerHTML = '<div class="td-err" data-testid="td-error">' +
        esc(state.error) + ' Press Retry to fetch again.</div>';
      return;
    }
    var shown = state.alerts.filter(function (a) {
      return state.filter === 'ALL' || a.sev === state.filter;
    });
    if (status) {
      status.textContent = state.retrying ? status.textContent :
        (shown.length + ' of ' + state.alerts.length + ' alerts · snapshot ' + age);
    }
    if (!list) return;
    if (!shown.length) {
      list.innerHTML = '<div class="td-empty" data-testid="td-empty">No ' +
        esc(state.filter.toLowerCase()) + ' alerts in this snapshot.</div>';
      return;
    }
    list.innerHTML = shown.map(function (a, i) { return cardHtml(a, i, age); }).join('');
  }

  function setStatus(root, msg) {
    var s = root.querySelector('[data-td="status"]');
    if (s) s.textContent = msg;
  }

  /* Re-fetch with exponential backoff. The Retry button is never dead:
   * every attempt updates the status line; final failure keeps the old
   * cards (if any) plus an honest error, and Retry stays enabled. */
  function loadWithBackoff(root, attempt) {
    attempt = attempt || 1;
    state.retrying = true;
    render(root);
    setStatus(root, attempt === 1 ? 'Fetching fixtures…' :
      'Retrying… (attempt ' + attempt + '/' + MAX_ATTEMPTS + ')');
    fetch(FIXTURES, { cache: 'no-store' }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }).then(function (d) {
      state.alerts = buildAlerts(d);
      state.updatedAt = (d.meta && d.meta.frozenAt) || new Date().toISOString();
      state.error = null;
      state.retrying = false;
      render(root);
    }).catch(function (err) {
      if (attempt < MAX_ATTEMPTS) {
        var delay = BASE_DELAY_MS * Math.pow(2, attempt - 1);
        setStatus(root, 'Fetch failed (' + err.message + '). Backing off ' +
          Math.round(delay / 100) / 10 + 's…');
        setTimeout(function () { loadWithBackoff(root, attempt + 1); }, delay);
      } else {
        state.retrying = false;
        state.error = 'Could not load alert fixtures after ' + MAX_ATTEMPTS +
          ' attempts (' + err.message + ').';
        render(root);
      }
    });
  }

  function init(hostId) {
    var root = typeof hostId === 'string' ? document.getElementById(hostId) : hostId;
    if (!root) return;
    var mount = root.querySelector('.td-wrap') || root;
    mount.querySelectorAll('[data-td-filter]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.getAttribute('data-td-filter');
        if (FILTERS.indexOf(f) >= 0) {
          state.filter = f;
          render(mount);
        }
      });
    });
    var retry = mount.querySelector('[data-td="retry"]');
    if (retry) retry.addEventListener('click', function () {
      if (!state.retrying) loadWithBackoff(mount, 1);
    });
    loadWithBackoff(mount, 1);
  }

  window.Calerts = { init: init, _buildAlerts: buildAlerts, _relAge: relAge };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      if (document.getElementById(ROOT_ID)) init(ROOT_ID);
    });
  } else if (document.getElementById(ROOT_ID)) {
    init(ROOT_ID);
  }
})();
