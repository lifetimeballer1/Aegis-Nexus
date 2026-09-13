/** TRACK-C / GUI-3 — lazy canvas network graph. Vanilla JS, no deps, no live calls.
 * Data: fetch('data/gui-fixtures.json') (frozen copy of ~/aegis-gui/fixtures.json).
 * Window scaling (deterministic): ALL x1.0 | 90D x1.0 | 30D x0.75 | 7D x0.45 | 24H x0.18.
 *   visible = stable-hash-sorted nodes sliced to ceil(N*f); hub counts shown as round(base*f).
 * Perf: nodes capped at 120, one rAF loop, DPR<=2, layout precomputed, IO-gated, reduced-motion static.
 */
const WINDOW_SCALE = { ALL: 1.0, '90D': 1.0, '30D': 0.75, '7D': 0.45, '24H': 0.18 };
/* ref-pin: major-node pill anchors, in label priority order. First unmatched node per keyword gets a pill. */
const PILL_KEYS = ['Communist Party of China', 'South China Sea', 'U.S. Department of Justice', 'U.S. Treasury', 'Middle East', 'China', 'Iran', 'Europe'];
let lastP = null;
let pillNodes = [];
let pillsBox = null;
const NODE_CAP = 120;
const DATA_URL = 'data/gui-fixtures.json';
let started = false;

function hashStr(s) {
  let h = 5381;
  const str = String(s || '');
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
  return h >>> 0;
}
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function relTime(iso, minusH) {
  const base = Date.parse(iso || '') || Date.now();
  const t = base - (minusH % 72) * 3600e3;
  const d = new Date(t);
  const hrs = Math.round((Date.now() - t) / 3600e3);
  const ago = hrs < 1 ? 'just now' : hrs < 24 ? hrs + 'h ago' : Math.round(hrs / 24) + 'd ago';
  return { label: d.toISOString().slice(0, 16).replace('T', ' ') + 'Z • ' + ago, href: d.toISOString() };
}

export function initCgraph() {
  if (started) return;
  const frame = document.getElementById('cgFrame');
  if (!frame) return; // not integrated yet — safe no-op
  started = true;
  const run = () => boot().catch(err => {
    const st = document.getElementById('cgStatus');
    if (st) st.textContent = 'Fixture load failed: ' + err.message;
  });
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => {
      for (const e of es) if (e.isIntersecting) { io.disconnect(); run(); break; }
    }, { rootMargin: '200px' });
    io.observe(frame);
  } else run();
}

async function boot() {
  const $ = id => document.getElementById(id);
  const frameEl = document.getElementById('cgFrame');
  const canvas = document.getElementById('cgCanvas'), svgBox = document.getElementById('cgSvgFallback'), status = document.getElementById('cgStatus'), cards = document.getElementById('cgCards');
  const res = await fetch(DATA_URL, { cache: 'no-store' });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  const fx = await res.json();
  const frozenAt = (fx.meta && fx.meta.frozenAt) || '';
  // ---- build node pool (cap 120) ----
  const pool = [];
  const stories = ((fx.headlines || {}).stories || []).map(s => ({
    label: s.title, outlet: s.source || 'Unknown outlet', cat: s.type || 'general', reports: 1, kind: 'story'
  }));
  const events = ((fx.headlines || {}).events || []).map(e => ({
    label: e.title, outlet: 'Aegis aggregate', cat: e.category || 'general', reports: +e.reports || 1, kind: 'event'
  }));
  const devs = ((fx.headlines || {}).topDevelopments || []).map(d => ({
    label: d.title, outlet: 'Aegis aggregate', cat: d.category || 'general', reports: 2, kind: 'story'
  }));
  for (const [domain, count] of Object.entries(fx.domainMix || {}))
    pool.push({ label: '#' + domain + ' (' + count + ')', outlet: 'Aegis aggregate', cat: domain, reports: Math.max(1, Math.round(count / 40)), kind: 'hub', base: count, hub: domain });
  for (const r of (fx.regions || []))
    pool.push({ label: '◈ ' + r.name, outlet: 'Aegis aggregate', cat: 'region', reports: +r.reports || 1, kind: 'hub', hub: r.name });
  for (const s of [...stories, ...events, ...devs]) pool.push(s);
  const nodes = pool.slice(0, NODE_CAP).map((n, i) => ({ ...n, id: i, h: hashStr(n.label + '|' + n.outlet) }));
  // precomputed layout: ring + hash jitter, pseudo-3D depth z in [-1,1]
  nodes.forEach((n, i) => {
    const a = (i / Math.max(1, nodes.length)) * Math.PI * 2;
    const j = (n.h % 100) / 100;
    n.bx = Math.cos(a) * (0.32 + j * 0.12); n.by = Math.sin(a) * (0.32 + j * 0.12); n.z = ((n.h >> 8) % 100) / 50 - 1;
  });
  // edges: shared outlet or shared cat (story/event only), hubs link to same-cat members
  const edges = [];
  const byCat = {};
  nodes.forEach(n => { (byCat[n.cat] = byCat[n.cat] || []).push(n.id); });
  nodes.forEach(n => {
    if (n.kind === 'hub') {
      for (const m of (byCat[n.hub] || byCat[n.cat] || [])) {
        if (m !== n.id && edges.length < 300) edges.push([n.id, m]);
      }
    }
  });
  for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
    if (edges.length >= 300) break;
    const a = nodes[i], b = nodes[j];
    if (a.kind === 'hub' || b.kind === 'hub') continue;
    if (a.outlet === b.outlet || a.cat === b.cat) edges.push([a.id, b.id]);
  }
  // ---- filter state ----
  const F = { win: 'ALL', sources: new Set(nodes.map(n => n.outlet)), cat: '', minRep: 0 };
  const srcBox = document.getElementById('cgSources'), catSel = document.getElementById('cgCat'), minRep = document.getElementById('cgMinRep'), minRepVal = document.getElementById('cgMinRepVal');
  [...new Set(nodes.map(n => n.outlet))].sort().forEach(s => {
    const lab = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = true; cb.value = s;
    cb.addEventListener('change', () => { cb.checked ? F.sources.add(s) : F.sources.delete(s); draw(); });
    lab.append(cb, document.createTextNode(' ' + s));
    srcBox.append(lab);
  });
  [...new Set(nodes.map(n => n.cat))].sort().forEach(c => {
    const o = document.createElement('option'); o.value = c; o.textContent = c; catSel.append(o);
  });
  catSel.addEventListener('change', () => { F.cat = catSel.value; draw(); });
  minRep.addEventListener('input', () => { F.minRep = +minRep.value; minRepVal.textContent = minRep.value; draw(); });
  document.getElementById('cgFiltersBtn').addEventListener('click', () => {
    const d = document.getElementById('cgDrawer'), open = d.hidden;
    d.hidden = !open; document.getElementById('cgFiltersBtn').setAttribute('aria-expanded', String(open));
    document.getElementById('cgFiltersBtn').textContent = open ? 'CLOSE FILTERS' : 'OPEN FILTERS';
  });
  document.querySelectorAll('#cgPills .cg-pill').forEach(p => p.addEventListener('click', () => {
    document.querySelectorAll('#cgPills .cg-pill').forEach(q => q.setAttribute('aria-pressed', 'false'));
    p.setAttribute('aria-pressed', 'true'); F.win = p.dataset.win; draw();
  }));
  // ---- visible set per window+filters ----
  function visible() {
    const f = WINDOW_SCALE[F.win] ?? 1;
    const sorted = [...nodes].sort((a, b) => a.h - b.h);
    const slice = new Set(sorted.slice(0, Math.max(4, Math.ceil(sorted.length * f))).map(n => n.id));
    return nodes.filter(n => slice.has(n.id) && F.sources.has(n.outlet) && (!F.cat || n.cat === F.cat) && n.reports >= F.minRep);
  }
  // ---- canvas renderer (lazy, one rAF) ----
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let raf = 0, angle = 0, scale = 1, ox = 0, oy = 0, running = false, pillTick = 0;
  function setupCanvas() {
    const dpr = Math.min(2, devicePixelRatio || 1);
    const r = frameEl.getBoundingClientRect();
    canvas.width = Math.max(300, r.width * dpr); canvas.height = 320 * dpr;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  }
  let ctx = canvas.getContext ? setupCanvas() : null;
  addEventListener('resize', () => { if (ctx) ctx = setupCanvas(); }, { passive: true });
  // pan + pinch zoom
  const pts = new Map(); let pinch0 = 0, scale0 = 1;
  canvas.addEventListener('pointerdown', e => { pts.set(e.pointerId, [e.clientX, e.clientY]); canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => {
    if (!pts.has(e.pointerId)) return;
    const prev = pts.get(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 1) { ox += e.clientX - prev[0]; oy += e.clientY - prev[1]; }
    else if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (!pinch0) { pinch0 = d; scale0 = scale; }
      else scale = Math.min(3, Math.max(0.5, scale0 * d / pinch0));
    }
  });
  const endPt = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch0 = 0; };
  canvas.addEventListener('pointerup', endPt); canvas.addEventListener('pointercancel', endPt);
  function frame2d(list) {
    const W = canvas.clientWidth || 360, H = 320;
    ctx.clearRect(0, 0, W, H);
    const cx = W / 2 + ox, cy = H / 2 + oy, R = Math.min(W, H) * 0.42 * scale;
    const P = new Map();    for (const n of list) {
      const rot = reduceMotion ? 0 : angle;
      const x = n.bx * Math.cos(rot) - n.z * 0.25 * Math.sin(rot);
      const depth = (n.z * Math.cos(rot) + 0.6) / 1.6; // 0..1 pseudo-depth
      const px = cx + x * R * 2.2, py = cy + n.by * R * 2.2;
      P.set(n.id, [px, py, depth]);
    }
    ctx.lineWidth = 1;
    for (const [a, b] of edges) {
      const A = P.get(a), B = P.get(b);
      if (!A || !B) continue;
      ctx.strokeStyle = 'rgba(63,197,255,' + (0.10 + 0.25 * Math.min(A[2], B[2])).toFixed(2) + ')';
      ctx.beginPath(); ctx.moveTo(A[0], A[1]); ctx.lineTo(B[0], B[1]); ctx.stroke();
    }
    for (const n of list) {
      const [px, py, depth] = P.get(n.id);
      const r = (n.kind === 'hub' ? 7 : 4) * (0.7 + depth * 0.6);
      ctx.beginPath(); ctx.arc(px, py, r, 0, 7);
      ctx.fillStyle = n.kind === 'hub' ? '#ffc857' : n.kind === 'event' ? '#fb923c' : '#3fc5ff';
      ctx.globalAlpha = 0.55 + depth * 0.45; ctx.fill(); ctx.globalAlpha = 1;
    }
    if (!reduceMotion) angle += 0.0035;
    lastP = P;
    pillTick++;
    if (pillTick % 20 === 0) placePills();
  }
  function svgFallback(list) {
    canvas.hidden = true; svgBox.hidden = false;
    const W = 360, H = 320, cx = 180, cy = 160, R = 120;
    let s = '<svg viewBox="0 0 360 320" width="100%" height="320" role="img" aria-label="Story network (static)">';
    for (const [a, b] of edges.slice(0, 120)) {
      const A = list.find(n => n.id === a), B = list.find(n => n.id === b);
      if (!A || !B) continue;
      const ax = cx + A.bx * R * 2.2, ay = cy + A.by * R * 2.2, bx = cx + B.bx * R * 2.2, by = cy + B.by * R * 2.2;
      s += '<line x1="' + ax.toFixed(1) + '" y1="' + ay.toFixed(1) + '" x2="' + bx.toFixed(1) + '" y2="' + by.toFixed(1) + '" stroke="#1b3854"/>';
    }
    for (const n of list.slice(0, 60)) {
      const px = cx + n.bx * R * 2.2, py = cy + n.by * R * 2.2;
      const c = n.kind === 'hub' ? '#ffc857' : n.kind === 'event' ? '#fb923c' : '#3fc5ff';
      s += '<circle cx="' + px.toFixed(1) + '" cy="' + py.toFixed(1) + '" r="' + (n.kind === 'hub' ? 6 : 4) + '" fill="' + c + '"/>';
    }
    svgBox.innerHTML = s + '</svg>';
  }
  function pickPills() {
    pillNodes = [];
    const used = new Set();
    const hubsFirst = [...nodes].sort((a, b) => (b.kind === 'hub') - (a.kind === 'hub'));
    for (const key of PILL_KEYS) {
      const hit = hubsFirst.find(n => !used.has(n.id) && n.label.toLowerCase().includes(key.toLowerCase()));
      if (hit) { used.add(hit.id); pillNodes.push({ node: hit, short: key }); }
      if (pillNodes.length >= 8) break;
    }
    buildPillDom();
  }
  function buildPillDom() {
    pillsBox = document.getElementById('cgNodePills');
    if (!pillsBox) return;
    pillsBox.innerHTML = '';
    pillNodes.forEach((p, i) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cg-nodepill';
      b.innerHTML = '<i aria-hidden="true"></i>' + esc(p.short);
      b.setAttribute('aria-label', 'Inspect node ' + p.node.label);
      b.addEventListener('click', () => showNodeDetail(p.node));
      pillsBox.append(b);
      p.el = b;
    });
    placePills();
  }
  function placePills() {
    if (!pillsBox || !lastP) return;
    for (const p of pillNodes) {
      const pos = lastP.get(p.node.id);
      if (!pos || !p.el) { if (p.el) p.el.hidden = true; continue; }
      p.el.hidden = false;
      p.el.style.left = Math.max(4, Math.min(pos[0], (frameEl.clientWidth || 360) - 4)) + 'px';
      p.el.style.top = Math.max(4, Math.min(pos[1], 316)) + 'px';
    }
  }
  function showNodeDetail(n) {
    const t = relTime(frozenAt, n.h);
    const q = 'https://www.google.com/search?q=' + encodeURIComponent(n.label);
    const html = '<article class="cg-card cg-detail" tabindex="0" id="cgDetailCard"><h4>' + esc(n.label) + '</h4>' +
      '<div class="cg-meta"><span>📰 ' + esc(n.outlet) + '</span><span>🕒 ' + esc(t.label) + '</span>' +
      '<span class="cg-badge">' + esc(n.cat) + ' • ' + n.reports + ' report' + (n.reports === 1 ? '' : 's') + '</span>' +
      '<a href="' + q + '" target="_blank" rel="noopener">Open link ↗</a></div></article>';
    cards.innerHTML = html + cards.innerHTML;
    const d = document.getElementById('cgDetailCard');
    if (d) d.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  function drawCards(list) {
    const items = list.filter(n => n.kind !== 'hub').slice(0, 30);
    cards.innerHTML = items.map(n => {
      const t = relTime(frozenAt, n.h);
      const q = 'https://www.google.com/search?q=' + encodeURIComponent(n.label);
      const badge = n.hub ? '' : '<span class="cg-badge">' + esc(n.cat) + ' • ' + n.reports + ' report' + (n.reports === 1 ? '' : 's') + '</span>';
      return '<article class="cg-card" tabindex="0"><h4>' + esc(n.label) + '</h4>' +
        '<div class="cg-meta"><span>📰 ' + esc(n.outlet) + '</span><span>🕒 ' + esc(t.label) + '</span>' + badge +
        '<a href="' + q + '" target="_blank" rel="noopener">Open link ↗</a></div></article>';
    }).join('') || '<p class="cg-sub">No stories match these filters.</p>';
  }
  function draw() {
    const list = visible();
    const f = WINDOW_SCALE[F.win] ?? 1;
    status.textContent = list.length + ' nodes • ' + edges.filter(([a, b]) => list.some(n => n.id === a) && list.some(n => n.id === b)).length +
      ' edges • ' + F.win + ' (×' + f + ') • fixture ' + (frozenAt || 'n/a').slice(0, 10);
    if (!ctx) { svgFallback(list); drawCards(list); return; }
    if (!running) { running = true; cancelAnimationFrame(raf); const loop = () => { frame2d(visible()); raf = requestAnimationFrame(loop); }; loop(); }
    drawCards(list);
  }
  draw();
  pickPills();  new IntersectionObserver(es => {
    for (const e of es) {
      if (e.isIntersecting && ctx && !running) draw();
      if (!e.isIntersecting && ctx) { running = false; cancelAnimationFrame(raf); }
    }
  }).observe(frameEl);
}
