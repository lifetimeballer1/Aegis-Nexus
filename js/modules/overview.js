/** Global Situation Overview — consumes real Global Pulse snapshot shape */

import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml, scoreToLevel } from '../core/utils.js';

function clampPct(n) {
  return Math.max(0, Math.min(100, Number(n) || 0));
}

export function renderOverview() {
  const el = document.getElementById('overviewBody');
  const updatedEl = document.getElementById('overviewUpdated');
  if (!el) return;

  const { snapshot, status } = getState();

  if (!snapshot) {
    el.innerHTML = `
      <div class="gp-state">
        ${status === 'loading' ? '<div class="gp-spinner"></div>' : ''}
        <div class="gp-state-title">${status === 'error' ? 'Data unavailable' : 'Loading\u2026'}</div>
        <div>${status === 'error' ? 'Public intelligence snapshot could not be loaded.' : 'Fetching the public intelligence snapshot.'}</div>
      </div>`;
    return;
  }

  const updated = snapshot.updatedAt || snapshot.lastSuccessfulRefresh || null;
  if (updatedEl) updatedEl.textContent = formatRelativeTime(updated);

  const tension = snapshot.tension ?? snapshot.globalTension ?? snapshot.score ?? null;
  const delta = snapshot.tensionDelta;
  const breakdown = snapshot.breakdownScores || {};
  const drivers = snapshot.driverSignals || {};
  const note = snapshot.dataNote || snapshot.sourceStatus || '';
  const early = snapshot.earlyWarning || null;

  const driverOrder = [
    'Conflict activity',
    'Diplomatic strain',
    'Economic pressure',
    'Market volatility',
    'Military posture',
    'Climate & humanitarian pressure'
  ];

  let driversHtml = '';
  for (const label of driverOrder) {
    const score = breakdown[label];
    const signal = drivers[label] || {};
    const num = typeof score === 'number' ? score : (signal.signalRatio != null ? signal.signalRatio * 100 : null);
    const level = scoreToLevel(num);
    const display = num != null ? Math.round(num) : '—';
    const meta = signal.matches != null
      ? `${signal.matches} matches · ${signal.sources || 0} sources`
      : '';
    driversHtml += `
      <div class="gp-meter">
        <div class="gp-meter-label">
          <span>${escapeHtml(label)}</span>
          <strong>${display}</strong>
        </div>
        <div class="gp-meter-bar">
          <div class="gp-meter-fill ${level}" style="width:${num != null ? clampPct(num) : 0}%"></div>
        </div>
        ${meta ? `<div style="font-size:10px;color:var(--muted-2);margin-top:2px">${escapeHtml(meta)}</div>` : ''}
      </div>`;
  }

  const tensionLevel = scoreToLevel(tension);
  const tensionDisplay = tension != null ? Math.round(tension) : '—';
  const deltaStr = delta != null
    ? (delta > 0 ? `↑ +${delta}` : delta < 0 ? `↓ ${delta}` : '→ 0')
    : '';

  el.innerHTML = `
    <div class="gp-grid gp-grid-2" style="margin-bottom:16px">
      <div class="gp-card">
        <div style="font-size:11px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px">Global Tension Index</div>
        <div style="display:flex;align-items:baseline;gap:10px">
          <div style="font-size:36px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1">${tensionDisplay}</div>
          ${deltaStr ? `<span style="font-size:14px;font-weight:700;color:${delta > 0 ? 'var(--red)' : delta < 0 ? 'var(--green)' : 'var(--muted)'}">${deltaStr}</span>` : ''}
        </div>
        <div class="gp-meter" style="margin-top:12px">
          <div class="gp-meter-bar" style="height:8px">
            <div class="gp-meter-fill ${tensionLevel}" style="width:${tension != null ? clampPct(tension) : 0}%"></div>
          </div>
        </div>
        <div style="font-size:11px;color:var(--muted);margin-top:8px">Composite open-data signal. Higher = greater combined geopolitical, military, diplomatic and economic pressure.</div>
      </div>
      <div class="gp-card">
        <div style="font-size:11px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">Key Drivers</div>
        ${driversHtml || '<div style="color:var(--muted)">No driver breakdown available</div>'}
      </div>
    </div>
    ${early ? `
      <div class="gp-card" style="margin-bottom:12px;border-color:var(--amber-dim)">
        <div style="font-size:11px;font-weight:700;color:var(--amber);letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px">Early Warning</div>
        <div style="font-size:13px;color:var(--text-secondary)">${escapeHtml(typeof early === 'string' ? early : (early.summary || early.message || JSON.stringify(early).slice(0, 200)))}</div>
      </div>` : ''}
    ${note ? `<div class="gp-card" style="font-size:12px;color:var(--text-secondary)">${escapeHtml(note)}</div>` : ''}
    <div style="margin-top:12px;font-size:11px;color:var(--muted-2)">
      Analytical indicator only — not an official government risk rating. Always verify against primary sources.
    </div>
  `;
}
