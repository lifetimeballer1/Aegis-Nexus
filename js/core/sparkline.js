/** Vendored SVG sparkline (fnando/sparkline pattern, zero-dep). Values only from canonical data. */
export function sparklineSVG(values, { w = 96, h = 28, stroke = '#62a0ff', fill = true, id = '' } = {}) {
  const pts = (Array.isArray(values) ? values : []).map(Number).filter(Number.isFinite).slice(-24);
  if (pts.length < 2) return '';
  const min = Math.min(...pts), max = Math.max(...pts), span = (max - min) || 1;
  const stepX = w / (pts.length - 1);
  const coords = pts.map((v, i) => [i * stepX, h - 3 - ((v - min) / span) * (h - 6)]);
  const line = coords.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const area = `${line} L${w},${h} L0,${h} Z`;
  const last = coords[coords.length - 1];
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true" focusable="false" role="img"${id ? ` aria-label="${id} trend"` : ''}>`
    + (fill ? `<path d="${area}" fill="${stroke}22"/>` : '')
    + `<path d="${line}" fill="none" stroke="${stroke}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>`
    + `<circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.4" fill="${stroke}"/></svg>`;
}
/** Vendored SVG bar strip (zero-dep companion to sparklineSVG).
 * Values only from canonical data; returns '' when history is absent
 * so point-in-time tiles stay honestly spark-free. */
export function barsSVG(values, { w = 96, h = 28, fill = '#62a0ff', id = '' } = {}) {
  const pts = (Array.isArray(values) ? values : []).map(Number).filter(Number.isFinite).slice(-18);
  if (pts.length < 2) return '';
  const max = Math.max(...pts, 0) || 1;
  const n = pts.length;
  const bw = w / n;
  const rects = pts.map((v, i) => {
    const bh = Math.max(2, (Math.max(0, v) / max) * (h - 2));
    const x = (i * bw + 1).toFixed(1);
    return `<rect x="${x}" y="${(h - bh).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${bh.toFixed(1)}" rx="1" fill="${fill}" opacity="${(0.35 + 0.65 * (i + 1) / n).toFixed(2)}"/>`;
  }).join('');
  return `<svg class="cc-minibars" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true" focusable="false" role="img"${id ? ` aria-label="${id} bars"` : ''}>${rects}</svg>`;
}
export function deltaChip(delta) {
  const n = Number(delta);
  if (!Number.isFinite(n) || n === 0) return '<span class="d flat">— 0%</span>';
  const cls = n > 0 ? 'up' : 'down';
  const arrow = n > 0 ? '↑' : '↓';
  return `<span class="d ${cls}">${arrow} ${Math.abs(n)}%</span>`;
}
