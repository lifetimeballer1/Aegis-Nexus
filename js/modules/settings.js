/** Settings & Preferences — device-local controls (Concept 06 governance theme).
 * Auto-refresh cadence, device-stored analyst data (acknowledgements,
 * briefing drafts, saved views) with honest byte counts and confirmed
 * clearing, plus build/about facts from canonical state. No accounts,
 * no permissions backend: everything here affects only this browser. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';

export const PREFS_KEY = 'gp.prefs.v1';
const STORE_KEYS = [
  ['gp.alertAck.v1', 'Alert acknowledgements'],
  ['gp.briefDrafts.v1', 'Briefing drafts'],
  ['gp.savedViews.v1', 'Saved views'],
  ['gp.mapLayers', 'Map layer prefs'],
  ['gp.mapFilter', 'Map filter'],
  ['gp.howToRead.v1', 'Onboarding flag'],
];

function esc(value) {
  return escapeHtml(String(value ?? ''));
}

export function loadPrefs() {
  try {
    const raw = JSON.parse(localStorage.getItem(PREFS_KEY) || '{}');
    return {
      autoRefresh: raw.autoRefresh !== false,
      intervalMin: [5, 10, 15, 30].includes(Number(raw.intervalMin)) ? Number(raw.intervalMin) : 5,
    };
  } catch { return { autoRefresh: true, intervalMin: 5 }; }
}

function savePrefs(prefs) {
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch {}
  window.dispatchEvent(new CustomEvent('gp:prefs-changed'));
}

function storeUsage() {
  return STORE_KEYS.map(([key, label]) => {
    let bytes = 0, count = null;
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return { key, label, bytes: 0, count: 0, present: false };
      bytes = raw.length;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        if (Array.isArray(parsed)) count = parsed.length;
        else if (Array.isArray(parsed.drafts)) count = parsed.drafts.length;
        else count = Object.keys(parsed).length;
      }
    } catch { count = null; }
    return { key, label, bytes, count, present: true };
  });
}

function fmtBytes(n) {
  if (!Number.isFinite(Number(n))) return '—';
  const v = Number(n);
  if (v >= 1048576) return `${(v / 1048576).toFixed(1)} MB`;
  if (v >= 1024) return `${(v / 1024).toFixed(1)} KB`;
  return `${v} B`;
}

export function renderSettings() {
  const el = document.getElementById('settingsBody');
  if (!el) return;
  const state = getState();
  const prefs = loadPrefs();
  const usage = storeUsage();
  const totalBytes = usage.reduce((n, u) => n + (u.bytes || 0), 0);
  const manifest = state.refreshManifest || {};
  const artifactCount = manifest.artifacts ? Object.keys(manifest.artifacts).length : 0;
  const vSummary = state.validationResults?.summary || {};

  el.innerHTML = `<div class="gp-dash-grid">
      <div class="gp-dash-panel"><h3>Refresh preferences</h3>
        <label style="display:flex;gap:8px;align-items:center;font-size:12px"><input id="prefAuto" type="checkbox"${prefs.autoRefresh ? ' checked' : ''}> Auto-refresh while visible</label>
        <label style="display:block;font-size:10px;color:var(--muted-2);margin-top:8px">Interval
          <select id="prefInterval" class="gp-map-search">${[5, 10, 15, 30].map(m => `<option value="${m}"${m === prefs.intervalMin ? ' selected' : ''}>Every ${m} minutes</option>`).join('')}</select></label>
        <div class="meta" style="font-size:10px;color:var(--muted-2);margin-top:6px">Applies to this browser immediately.</div></div>
      <div class="gp-dash-panel"><h3>About this build</h3>
        <div class="meta" style="font-size:11px">Aegis Nexus · evidence-backed public-source monitor</div>
        <div class="meta" style="font-size:11px">Data refresh: ${manifest.generatedAt ? esc(formatRelativeTime(manifest.generatedAt)) : '—'} · ${artifactCount ? `${artifactCount} hashed artifacts` : 'manifest unavailable'}</div>
        <div class="meta" style="font-size:11px">Validation: ${vSummary.run ? `${vSummary.passed}/${vSummary.run} gates passed` : 'no validation run recorded'}</div></div>
    </div>
    <div class="gp-dash-panel" style="margin-top:8px"><h3>Device data <span style="font-weight:400;color:var(--muted);font-size:10px">${esc(fmtBytes(totalBytes))} stored · never uploaded</span></h3>
      <div class="gp-dash-list">${usage.map(u => `<div class="gp-dash-row"><div class="grow"><div class="title" style="font-size:11px">${esc(u.label)}</div>`
        + `<div class="meta">${u.present ? `${u.count === null ? '' : `${u.count} records · `}${esc(fmtBytes(u.bytes))}` : 'empty'}</div></div>`
        + (u.present ? `<button class="gp-btn" data-store-clear="${esc(u.key)}" type="button">Clear</button>` : '') + `</div>`).join('')}</div>
      <div style="margin-top:8px"><button class="gp-btn" data-store-clear-all type="button">Clear all device data</button></div>
    </div>`;

  el.querySelector('#prefAuto')?.addEventListener('change', (e) => {
    const p = loadPrefs(); p.autoRefresh = !!e.target.checked; savePrefs(p);
  });
  el.querySelector('#prefInterval')?.addEventListener('change', (e) => {
    const p = loadPrefs(); p.intervalMin = Number(e.target.value) || 5; savePrefs(p);
  });
  const wipe = (keys) => {
    const label = keys.length > 1 ? `${keys.length} device stores` : 'this device store';
    if (!window.confirm(`Clear ${label}? This cannot be undone.`)) return;
    for (const k of keys) { try { localStorage.removeItem(k); } catch {} }
    renderSettings();
  };
  el.querySelectorAll('[data-store-clear]').forEach(b => b.addEventListener('click', () => wipe([b.dataset.storeClear])));
  el.querySelector('[data-store-clear-all]')?.addEventListener('click', () => wipe(STORE_KEYS.map(([k]) => k).concat([PREFS_KEY])));
}
