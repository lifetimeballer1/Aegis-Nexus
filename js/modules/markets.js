/** Market Context — real public marketData.indicators, clearly labeled DELAYED. */

import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

let showAll = false;
let marketFilter = 'all';
let marketSort = 'movers';
const DEFAULT_VISIBLE = 5;
const MAX_VISIBLE = 20;

/* Filter buckets derived from the public symbols file
 * (update_market_data.py WATCH kinds: index/volatility/commodity/crypto/
 * fx/rates/equity) plus each symbol's own name/ticker text — no outside
 * taxonomy. Anything that matches none of the four commodity/macro buckets
 * (indices, single-name equities, volatility, crypto) falls into Other so
 * no indicator is ever stranded by a filter. */
const BUCKETS = [
  ['all', 'All'],
  ['energy', 'Energy'],
  ['metals', 'Metals'],
  ['macro-fx', 'Macro-FX'],
  ['agri', 'Agri'],
  ['other', 'Other'],
];
const BUCKET_LABEL = Object.fromEntries(BUCKETS);

export function marketBucket(item) {
  const kind = String(item?.type || item?.kind || '').toLowerCase();
  const text = `${item?.name || ''} ${item?.symbol || item?.ticker || ''}`.toLowerCase();
  if (/wheat|corn|soy|coffee|sugar|cotton|cocoa|grain|lumber|oats|rice|agri/.test(text)) return 'agri';
  if (/wti|brent|crude|\boil\b|nat\.?\s*gas|gasoline|heating.?oil|energy|cl=f|bz=f|ng=f/.test(text)) return 'energy';
  if (/gold|silver|copper|platinum|palladium|\bmetal\b|gc=f|si=f|hg=f|plt=f|pal=f/.test(text)) return 'metals';
  if (kind === 'fx' || kind === 'rates' || kind === 'rate' || kind === 'bond' || kind === 'currency'
    || /yield|treasury|bond|\bfx\b|euro|dollar|\byen\b|peso|rupee|yuan|franc|currency|exchange|interest/.test(text)) return 'macro-fx';
  return 'other';
}

function numericChange(item) {
  const value = item?.changePercent ?? item?.changePct ?? item?.pct ?? item?.change;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function absMove(item) {
  const change = numericChange(item);
  return change === null ? -Infinity : Math.abs(change);
}

export function sortMarkets(list, sort) {
  const copy = list.slice();
  if (sort === 'az') {
    copy.sort((a, b) => String(a.name || a.symbol || '').localeCompare(String(b.name || b.symbol || '')));
  } else {
    copy.sort((a, b) => absMove(b) - absMove(a));
  }
  return copy;
}

function formatPrice(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value ?? '—');
}

export function renderMarkets() {
  const el = document.getElementById('marketsBody');
  if (!el) return;

  const { snapshot, markets } = getState();
  let items = [];
  let meta = {};

  if (Array.isArray(markets)) {
    items = markets;
  } else if (markets?.indicators) {
    items = markets.indicators;
    meta = markets;
  } else if (snapshot?.marketData?.indicators) {
    items = snapshot.marketData.indicators;
    meta = snapshot.marketData;
  } else if (snapshot?.markets) {
    items = Array.isArray(snapshot.markets)
      ? snapshot.markets
      : Object.entries(snapshot.markets || {}).map(([k, v]) => ({ name: k, ...v }));
  } else if (snapshot?.marketPulse) {
    items = snapshot.marketPulse;
  }

  const allItems = items.filter(item => item && typeof item === 'object');
  const marketsCapped = allItems.length > MAX_VISIBLE;
  items = allItems.slice(0, MAX_VISIBLE);

  if (!items.length) {
    el.innerHTML = `
      <div class="gp-state">
        <div class="gp-state-title">Market data unavailable</div>
        <div>Public delayed market feed is not present in the current snapshot.</div>
      </div>`;
    return;
  }

  const updated = meta.updatedAt || snapshot?.updatedAt;
  const stamp = document.getElementById('marketsUpdated');
  if (stamp && updated) stamp.textContent = `Updated ${formatRelativeTime(updated)}`;
  const provider = meta.provider || meta.source || 'Public delayed feed';

  const counts = { all: items.length };
  for (const [key] of BUCKETS) {
    if (key === 'all') continue;
    counts[key] = items.filter(item => marketBucket(item) === key).length;
  }
  const filtered = marketFilter === 'all' ? items : items.filter(item => marketBucket(item) === marketFilter);
  const ordered = sortMarkets(filtered, marketSort);
  const visible = showAll ? ordered : ordered.slice(0, DEFAULT_VISIBLE);
  const changes = filtered.map(numericChange).filter(value => value !== null);
  const gainers = changes.filter(value => value > 0).length;
  const decliners = changes.filter(value => value < 0).length;
  const label = BUCKET_LABEL[marketFilter] || marketFilter;

  const chips = BUCKETS.map(([key, name]) =>
    `<button class="gp-filter${marketFilter === key ? ' active' : ''}" data-market-filter="${key}" type="button" aria-pressed="${marketFilter === key ? 'true' : 'false'}">${escapeHtml(name)} (${counts[key] ?? 0})</button>`
  ).join('');
  const sortBtns = [
    ['movers', 'Movers |Δ%|'],
    ['az', 'A–Z'],
  ].map(([key, name]) =>
    `<button class="gp-filter${marketSort === key ? ' active' : ''}" data-market-sort="${key}" type="button" aria-pressed="${marketSort === key ? 'true' : 'false'}">${escapeHtml(name)}</button>`
  ).join('');

  const cards = visible.map(m => {
    const name = m.name || m.symbol || m.ticker || m.exchange || '—';
    const price = m.price ?? m.last ?? m.close ?? '—';
    const change = numericChange(m);
    const changeStr = change === null ? '—' : `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
    const changeClass = change === null ? '' : change > 0 ? 'gp-market-up' : change < 0 ? 'gp-market-down' : 'gp-market-flat';
    const state = m.sessionStatus || m.marketState || m.status || '';
    const marketTime = m.marketTime || m.updatedAt || '';
    const sourceUrl = m.sourceUrl || m.url || '';
    const sourceLink = /^https?:\/\//i.test(String(sourceUrl))
      ? `<a href="${escapeHtml(String(sourceUrl))}" target="_blank" rel="noopener noreferrer" style="color:var(--sev-info);text-decoration:none">Source ↗</a>`
      : '';

    return `
      <div class="gp-card" data-market-bucket="${marketBucket(m)}">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">${escapeHtml(String(name))}</div>
        <div style="font-size:18px;font-weight:700;font-variant-numeric:tabular-nums">${escapeHtml(formatPrice(price))}</div>
        <div class="${changeClass}" style="font-size:13px;font-weight:600;margin-top:2px">${escapeHtml(changeStr)}</div>
        ${state ? `<div style="font-size:10px;color:var(--muted-2);margin-top:3px">${escapeHtml(String(state))}</div>` : ''}
        ${marketTime ? `<div style="font-size:9px;color:var(--muted-2);margin-top:3px">${escapeHtml(String(marketTime))}</div>` : ''}
        ${sourceLink ? `<div style="font-size:10px;margin-top:5px">${sourceLink}</div>` : ''}
      </div>`;
  }).join('');

  el.innerHTML = `
    <div style="font-size:11px;color:var(--muted);margin-bottom:10px">
      ${escapeHtml(provider)} · Updated ${formatRelativeTime(updated)} · <span class="gp-badge delayed">DELAYED</span>
    </div>
    <div class="gp-filter-row gp-mkt-filters" role="group" aria-label="Filter markets by category">${chips}</div>
    <div class="gp-filter-row gp-mkt-sort" role="group" aria-label="Sort markets"><span style="font-size:11px;color:var(--muted);align-self:center">Sort:</span>${sortBtns}</div>
    <div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px">
      <span class="gp-brain-chip">${marketsCapped ? `${items.length} of ${allItems.length}` : items.length} tracked indicators</span>
      <span class="gp-brain-chip">${gainers} advancing</span>
      <span class="gp-brain-chip">${decliners} declining</span>
    </div>
    ${visible.length ? `<div class="gp-grid gp-grid-3">${cards}</div>` : `<div class="gp-state"><div class="gp-state-title">No ${escapeHtml(label)} indicators</div><div>Nothing in the current snapshot matches this filter.</div></div>`}
    ${filtered.length > DEFAULT_VISIBLE ? `<button id="gpMarketsMore" class="gp-btn" type="button" style="margin-top:9px;width:100%">${showAll ? 'Show fewer' : `See more markets (${filtered.length - DEFAULT_VISIBLE})`}</button>` : ''}
    <div style="margin-top:12px;font-size:11px;color:var(--muted-2)">
      Prices are DELAYED / END-OF-DAY or public free-tier. This is market context, not real-time trading data or investment advice.
    </div>
  `;

  el.querySelectorAll('[data-market-filter]').forEach(btn => btn.addEventListener('click', () => {
    marketFilter = btn.dataset.marketFilter; showAll = false; renderMarkets();
  }));
  el.querySelectorAll('[data-market-sort]').forEach(btn => btn.addEventListener('click', () => {
    marketSort = btn.dataset.marketSort; showAll = false; renderMarkets();
  }));
  el.querySelector('#gpMarketsMore')?.addEventListener('click', () => {
    showAll = !showAll;
    renderMarkets();
  });
}
