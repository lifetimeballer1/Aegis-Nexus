/* TRACK-F — Overview landing builder (GUI Day2).
   Fixtures-backed, self-contained: zero imports, single data source
   fetch(data/gui-fixtures.json). Each panel is guarded — one bad panel
   can never blank the others. Nothing fabricated: absent fields render
   honest empty states. Vanilla JS only, no build step. */

(function () {
  var FIXTURES_URL = "data/gui-fixtures.json";
  var HOST_ID = "coverview";
  var booted = false;

  function esc(s) {
    var str = String(s == null ? "" : s);
    return str.replace(/[&<>"']/g, function (c) {
      if (c === "&") return "&amp;";
      if (c === "<") return "&lt;";
      if (c === ">") return "&gt;";
      if (c === '"') return "&quot;";
      return "&#39;";
    });
  }
  function num(v, fb) {
    var n = Number(v);
    return Number.isFinite(n) ? n : (fb == null ? 0 : fb);
  }
  function q(host, sel) { return host.querySelector(sel); }
  function setText(host, sel, txt) {
    var el = host.querySelector(sel);
    if (el) el.textContent = txt;
  }

  /* Tile derivations, all from the frozen fixtures (documented):
     active events = signals.liveEvents; high priority = signals.conflicts
     (tracked conflicts); emerging = headlines.events with low/limited/
     moderate confidence; critical = headlines.events with high/confirmed
     confidence; regions = regions.length; sources = sources.online/total. */
  function tileValues(d) {
    var sig = d.signals || {};
    var evts = (d.headlines && d.headlines.events) || [];
    var lo = 0, hi = 0, i, cf;
    for (i = 0; i < evts.length; i++) {
      cf = String(evts[i].confidence || "").toLowerCase();
      if (/high|confirmed/.test(cf)) hi++;
      else if (/low|limited|moderate/.test(cf)) lo++;
    }
    var src = d.sources || {};
    return [
      { v: String(num(sig.liveEvents)), l: "Active events", t: "tile-active-events", edge: "" },
      { v: String(num(sig.conflicts)), l: "High priority", t: "tile-high-priority", edge: "edge-red" },
      { v: String(lo), l: "Emerging risks", t: "tile-emerging-risks", edge: "edge-amber" },
      { v: String(hi), l: "Critical alerts", t: "tile-critical-alerts", edge: "edge-red" },
      { v: String(Array.isArray(d.regions) ? d.regions.length : 0), l: "Regions", t: "tile-regions", edge: "" },
      { v: num(src.online) + " / " + num(src.total_collector), l: "Sources online", t: "tile-sources-online", edge: "edge-green" }
    ];
  }

  function renderTiles(host, d) {
    var box = q(host, '[data-tf="tiles"]');
    if (!box) return;
    try {
      box.innerHTML = tileValues(d).map(function (t) {
        return '<div class="tf-tile ' + t.edge + '" role="listitem">' +
          '<span class="tf-v tf-mono" data-testid="' + t.t + '">' + esc(t.v) + "</span>" +
          '<span class="tf-l">' + esc(t.l) + "</span></div>";
      }).join("");
    } catch (e) { /* keep skeleton fallback */ }
  }

  function renderTension(host, d) {
    try {
      var t = d.tension || {};
      var idx = t.index == null ? null : Number(t.index);
      if (idx != null && !Number.isFinite(idx)) idx = null;
      var delta = num(t.delta, 0);
      var dstr = (delta > 0 ? "+" : "") + delta;
      setText(host, '[data-tf-val="tension"]', idx == null ? "--" : String(idx));
      setText(host, '[data-tf-val="tdelta"]', dstr);
      var bar = q(host, '[data-tf-val="tbar"]');
      if (bar && idx != null) bar.style.width = Math.max(0, Math.min(100, idx)) + "%";
      var drv = (t.earlyWarning && t.earlyWarning.strongestDriver) || t.strongestDriver || "";
      setText(host, '[data-tf-val="tdriver"]', drv ? ("Strongest driver: " + drv) : "Tension snapshot");
      var pill = q(host, '[data-testid="tension-pill"]');
      if (pill) pill.setAttribute("aria-label", "Tension index " + (idx == null ? "unknown" : idx) + ", change " + dstr);
    } catch (e) { /* keep skeleton fallback */ }
  }

  function renderHeadlines(host, d) {
    var box = q(host, '[data-tf="headlines"]');
    if (!box) return;
    try {
      var stories = (d.headlines && d.headlines.stories) || [];
      var top = stories.slice(0, 4);
      if (!top.length) return; // keep honest empty state
      var html = '<div class="tf-hlhead"><span class="tf-cardh">Top headlines</span>' +
        '<a class="tf-viewall" href="#section-briefings">View all &rarr;</a></div>';
      html += top.map(function (s) {
        return '<div class="tf-hlrow"><span class="tf-hldot" aria-hidden="true"></span>' +
          "<div><div class=\"tf-hltitle\">" + esc(s.title || "Untitled") + "</div>" +
          '<div class="tf-hlsrc">' + esc(s.source || "Unknown source") + "</div></div></div>";
      }).join("");
      box.innerHTML = html;
    } catch (e) { /* keep skeleton fallback */ }
  }

  function renderFresh(host, d) {
    try {
      var meta = d.meta || {};
      var frozen = meta.frozenAt ? String(meta.frozenAt).slice(0, 16).replace("T", " ") + "Z" : "unknown";
      var src = d.sources || {};
      setText(host, '[data-tf="fresh"]',
        "Feed status: snapshot " + frozen + " · " + num(src.online) + "/" +
        num(src.total_collector) + " sources online · " + num(src.onlineEmpty) + " stale · " + num(src.failed) + " failing");
    } catch (e) { /* keep skeleton fallback */ }
  }

  function paint(host, d) {
    renderTiles(host, d || {});
    renderTension(host, d || {});
    renderHeadlines(host, d || {});
    renderFresh(host, d || {});
  }

  function init(hostId) {
    var host = document.getElementById(hostId || HOST_ID);
    if (!host) return false;
    fetch(FIXTURES_URL, { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (d) { paint(host, d); })
      .catch(function () { paint(host, {}); });
    return true;
  }

  function autoBoot() {
    if (booted) return;
    booted = true;
    if (document.getElementById(HOST_ID)) init(HOST_ID);
  }

  window.Coverview = { init: init };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoBoot);
  else autoBoot();
})();
