/** Market Context — real public marketData.indicators, clearly labeled DELAYED. */

import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

let showAll = false;
const DEFAULT_VISIBLE = 5;
const MAX_VISIBLE = 20;

function numericChange(item) {
  const value = item?.changePercent ?? item?.changePct ?? item?.pct ?? item?.change;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
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

  items = items.filter(item => item && typeof item === 'object').slice(0, MAX_VISIBLE);

  if (!items.length) {
    el.innerHTML = `
      <div class="gp-state">
        <div class="gp-state-title">Market data unavailable</div>
        <div>Public delayed market feed is not present in the current snapshot.</div>
      </div>`;
    return;
  }

  const updated = meta.updatedAt || snapshot?.updatedAt;
  const provider = meta.provider || meta.source || 'Public delayed feed';
  const visible = showAll ? items : items.slice(0, DEFAULT_VISIBLE);
  const changes = items.map(numericChange).filter(value => value !== null);
  const gainers = changes.filter(value => value > 0).length;
  const decliners = changes.filter(value => value < 0).length;

  el.innerHTML = `
    <div style="font-size:11px;color:var(--muted);margin-bottom:10px">
      ${escapeHtml(provider)} · Updated ${formatRelativeTime(updated)} · <span class="gp-badge delayed">DELAYED</span>
    </div>
    <div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px">
      <span class="gp-brain-chip">${items.length} tracked indicators</span>
      <span class="gp-brain-chip">${gainers} advancing</span>
      <span class="gp-brain-chip">${decliners} declining</span>
    </div>
    <div class="gp-grid gp-grid-3">
      ${visible.map(m => {
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
          <div class="gp-card">
            <div style="font-size:11px;color:var(--muted);margin-bottom:4px">${escapeHtml(String(name))}</div>
            <div style="font-size:18px;font-weight:700;font-variant-numeric:tabular-nums">${escapeHtml(formatPrice(price))}</div>
            <div class="${changeClass}" style="font-size:13px;font-weight:600;margin-top:2px">${escapeHtml(changeStr)}</div>
            ${state ? `<div style="font-size:10px;color:var(--muted-2);margin-top:3px">${escapeHtml(String(state))}</div>` : ''}
            ${marketTime ? `<div style="font-size:9px;color:var(--muted-2);margin-top:3px">${escapeHtml(String(marketTime))}</div>` : ''}
            ${sourceLink ? `<div style="font-size:10px;margin-top:5px">${sourceLink}</div>` : ''}
          </div>`;
      }).join('')}
    </div>
    ${items.length > DEFAULT_VISIBLE ? `<button id="gpMarketsMore" class="gp-btn" type="button" style="margin-top:9px;width:100%">${showAll ? 'Show fewer' : `See more markets (${items.length - DEFAULT_VISIBLE})`}</button>` : ''}
    <div style="margin-top:12px;font-size:11px;color:var(--muted-2)">
      Prices are DELAYED / END-OF-DAY or public free-tier. This is market context, not real-time trading data or investment advice.
    </div>
  `;

  el.querySelector('#gpMarketsMore')?.addEventListener('click', () => {
    showAll = !showAll;
    renderMarkets();
  });
}
