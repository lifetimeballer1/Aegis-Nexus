/* TRACK-E — BRIEFINGS tab. Vanilla JS, fixtures-backed.
   Renders intelligence brief cards from data/gui-fixtures.json
   (headlines.stories + topDevelopments + events). Sources sacred:
   attribution strings copied verbatim, never edited. */
'use strict';

const FIXTURES_URL = 'data/gui-fixtures.json';
let query = '';

/* ---- thumbnails: build-time manifest + category SVG fallback (never broken) ---- */
let thumbManifest = null;
function thumbSlug(t) { return String(t || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48); }
const THUMB_CATS = ['geopolitical', 'economic', 'indo-pacific', 'domestic', 'general', 'generic', 'regional', 'cartel', 'international', 'news', 'diplomatic', 'conflict', 'political'];
function thumbFallback(cat) {
  const c = String(cat || '').toLowerCase().trim();
  if (THUMB_CATS.indexOf(c) >= 0) return c;
  return 'generic';
}
function thumbFor(title, cat) {
  const fb = 'assets/thumbs/fallback-' + thumbFallback(cat) + '.svg';
  const f = thumbManifest && thumbManifest[thumbSlug(title)];
  return { src: f ? ('assets/thumbs/' + f) : fb, fb: fb };
}
function thumbImg(title, cat, cls) {
  const t = thumbFor(title, cat);
  return '<img class="' + cls + '" src="' + t.src + '" alt="" loading="lazy" onerror="this.onerror=null;this.src=\'' + t.fb + '\'">';
}
function loadThumbs(rerender) {
  fetch('assets/thumbs/manifest.json', { headers: { Accept: 'application/json' } })
    .then(function (r) { if (!r.ok) throw new Error('no manifest'); return r.json(); })
    .then(function (m) { thumbManifest = (m && m.map) || {}; if (rerender) { try { rerender(); } catch (e) {} } })
    .catch(function () {});
}

function esc(value) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return map[c] || c; });
}
function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); }

function collectBriefs(fx) {
  const out = [];
  const seen = {};
  function push(b) {
    const k = norm(b.title);
    if (!k || seen[k]) return;
    seen[k] = 1;
    out.push(b);
  }
  const stories = Array.isArray(fx && fx.headlines && fx.headlines.stories) ? fx.headlines.stories : [];
  for (const s of stories) {
    if (!s || typeof s !== 'object') continue;
    push({ title: s.title || '', source: s.source || 'source unknown', time: s.publishedAt || s.time || '', category: s.type || s.category || 'general', brief: s.brief || s.summary || s.dek || '', confidence: s.confidence || '' });
  }
  const pools = [fx && fx.headlines && fx.headlines.topDevelopments, fx && fx.headlines && fx.headlines.events];
  for (const pool of pools) {
    const arr = Array.isArray(pool) ? pool : [];
    for (const s of arr) {
      if (!s || typeof s !== 'object') continue;
      push({ title: s.title || '', source: s.source || 'source unknown', time: s.publishedAt || s.time || '', category: s.category || s.type || 'general', brief: s.brief || s.summary || '', confidence: s.confidence || '', reports: s.reports });
    }
  }
  const extra = Array.isArray(fx && fx.briefs) ? fx.briefs : (Array.isArray(fx && fx.intel) ? fx.intel : []);
  for (const s of extra) {
    if (!s || typeof s !== 'object') continue;
    push({ title: s.title || '', source: s.source || 'source unknown', time: s.publishedAt || s.time || '', category: s.category || 'general', brief: s.brief || s.body || s.summary || '', confidence: s.confidence || '' });
  }
  return out;
}

function confClass(c) {
  const s = String(c || '').toLowerCase();
  if (s === 'high' || s === 'confirmed' || s === 'critical') return 'conf-high';
  if (s === 'moderate' || s === 'likely' || s === 'watch') return 'conf-moderate';
  if (s === 'low' || s === 'limited' || s === 'info') return 'conf-low';
  return '';
}

function cardHTML(b, i) {
  const conf = b.confidence ? '<span class="te-tag ' + confClass(b.confidence) + '">' + esc(b.confidence) + '</span>' : '';
  const reps = (b.reports != null && b.reports !== '') ? '<span class="te-tag">' + esc(String(b.reports)) + ' reports</span>' : '';
  const body = b.brief
    ? esc(b.brief)
    : ('Full brief: ' + esc(b.title) + ' — filed under ' + esc(b.category || 'general') + ' via ' + esc(b.source) + '.');
  return '<article class="te-card" data-testid="te-card-' + i + '">'
    + '<div class="te-card-top">' + thumbImg(b.title, b.category, 'te-thumb')
    + '<div class="te-card-main"><h3 class="te-card-title">' + esc(b.title) + '</h3>'
    + '<div class="te-card-meta">' + esc(b.source) + (b.time ? ' &middot; ' + esc(String(b.time)) : '') + (b.category ? ' &middot; ' + esc(String(b.category)) : '') + '</div>'
    + '<div class="te-tags"><span class="te-tag">' + esc(b.category || 'general') + '</span>' + conf + reps + '</div></div></div>'
    + '<details class="te-brief" data-testid="te-expand-' + i + '"><summary>Read full brief</summary><div class="te-brief-body">' + body + '</div></details>'
    + '</article>';
}

function render(fx) {
  const host = document.getElementById('cbriefsBody');
  if (!host) return;
  const all = collectBriefs(fx);
  const q = norm(query);
  const list = q ? all.filter(function (b) { return norm(b.title + ' ' + b.source + ' ' + b.category + ' ' + b.brief).includes(q); }) : all;
  const frozen = (fx && fx.meta && fx.meta.frozenAt) ? esc(fx.meta.frozenAt) : '';
  let html = '<div class="te-head"><h2 class="te-title">Briefings</h2>'
    + (frozen ? '<span class="te-meta">frozen ' + frozen + '</span>' : '') + '</div>'
    + '<div class="te-toolbar"><input id="teSearch" data-testid="te-search" class="te-search" type="search" placeholder="Search briefs…" aria-label="Search briefs" value="' + esc(query) + '">'
    + '<span class="te-count" data-testid="te-count">' + list.length + ' / ' + all.length + '</span></div>';
  if (!list.length) {
    html += '<div class="gp-state" data-testid="te-empty"><div class="gp-state-title">No briefs match</div><div>Try a different search.</div></div>';
  } else {
    html += '<div class="te-grid">' + list.map(function (b, i) { return cardHTML(b, i); }).join('') + '</div>';
  }
  host.innerHTML = html;
  const input = document.getElementById('teSearch');
  if (input) {
    input.addEventListener('input', function (e) {
      query = e.target.value || '';
      render(fx);
      const n = document.getElementById('teSearch');
      if (n) { n.focus(); try { n.setSelectionRange(n.value.length, n.value.length); } catch (e2) {} }
    });
  }
}

async function paint() {
  const host = document.getElementById('cbriefsBody');
  if (!host) return;
  try {
    const res = await fetch(FIXTURES_URL, { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error('fixtures HTTP ' + res.status);
    const fx = await res.json();
    render(fx);
    loadThumbs(function () { render(fx); });
  } catch (e) {
    host.innerHTML = '<div class="gp-state" data-testid="te-error"><div class="gp-state-title">Briefings unavailable</div><div>Could not load fixtures.</div></div>';
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', paint);
else paint();

export { paint as paintBriefings, render as renderBriefings, collectBriefs };
