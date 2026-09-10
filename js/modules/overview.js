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
        <div class="gp-state-title">${status === 'error' ? 'Data unavailable' : 'Loading…'}</div>
        <div>Public intelligence snapshot could not be loaded.</div>
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
  const tb = snapshot.tensionBreakdown || null;
  const computedAt = snapshot.tensionComputedAt || null;
  const stale = snapshot.tensionStale === true;

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
        <div style="font-size:11px;color:var(--muted);margin-top:8px">Composite open-data signal. Higher = greater combined geopolitical, military, diplomatic and economic pressure.${snapshot.scoreVersion ? ` Score model v${escapeHtml(String(snapshot.scoreVersion))}.` : ''}</div>
        ${tb ? `<div style="font-size:10px;color:var(--muted-2);margin-top:6px">Base drivers ${Math.round(Number(tb.base) || 0)} + story pressure ${escapeHtml(String(tb.storyPressure ?? 0))} (cap ${escapeHtml(String(tb.storyPressureCap ?? 30))}) from ${escapeHtml(String(tb.eligibleStories ?? 0))} open critical/high stor${Number(tb.eligibleStories) === 1 ? 'y' : 'ies'}.</div>` : ''}
        ${tb && Array.isArray(tb.topStories) && tb.topStories.length ? `<div style="font-size:10px;color:var(--muted-2);margin-top:6px">Top contributors: ${tb.topStories.slice(0, 3).map(s => `${escapeHtml(String(s.title || '').slice(0, 60))} (${escapeHtml(String(s.contribution))})`).join(' · ')}</div>` : ''}
        ${stale ? `<div class="gp-honest" style="margin-top:8px">Tension was last computed ${escapeHtml(computedAt ? formatRelativeTime(computedAt) : 'previously')} — the next canonical refresh recomputes it.</div>` : ''}
      </div>
      <div class="gp-card">
        <div style="font-size:11px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">Key Drivers</div>
        ${driversHtml || '<div style="color:var(--muted)">No driver breakdown available</div>'}
      </div>
    </div>
    ${early ? `
      <div class="gp-card" style="margin-bottom:12px;border-color:var(--amber-dim)">
        <div class="gp-row-between" style="margin-bottom:6px">
          <div style="font-size:11px;font-weight:700;color:var(--amber);letter-spacing:.08em;text-transform:uppercase">Early Warning</div>
          <span class="gp-sev ${early.level === 'HIGH' ? 'sev-critical' : early.level === 'ELEVATED' ? 'sev-high' : 'sev-medium'}">${escapeHtml(String(early.level || 'WATCH'))}</span>
        </div>
        <div style="font-size:13px;color:var(--text-secondary)">${escapeHtml(early.summary || early.message || '')}</div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;font-size:10px;color:var(--muted-2)">
          <span>Momentum ${early.momentum != null ? escapeHtml(String(early.momentum)) : '—'}</span>
          <span>Direction ${escapeHtml(String(early.direction || 'stable'))}</span>
          <span>Strongest driver ${escapeHtml(String(early.strongestDriver || '—'))}${early.strongestDriverScore != null ? ` (${escapeHtml(String(early.strongestDriverScore))})` : ''}</span>
          ${early.storyDriver ? `<span>Top story: ${escapeHtml(String(early.storyDriver).slice(0, 90))}</span>` : ''}
        </div>
      </div>` : ''}
    ${note ? `<div class="gp-card" style="font-size:12px;color:var(--text-secondary)">${escapeHtml(note)}</div>` : ''}
    <div style="margin-top:12px;font-size:11px;color:var(--muted-2)">
      Analytical indicator only — not an official government risk rating. Always verify against primary sources.
    </div>
  `;
}
