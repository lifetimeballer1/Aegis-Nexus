/** Global Pulse — isolated application boot with app-shell view routing. */
import { loadCoreData } from './core/fetch.js';
import { subscribe } from './core/state.js';
import { CONFIG } from './core/config.js';
import { setupDrawer } from './core/drawer.js';
import { setupRouter, showView, currentView, onActivate } from './core/router.js';

const modules = {};
const targets = {
  dashboard: 'dashboardBody',
  alerts: 'alertsBody',
  timeline: 'timelineBody',
  briefings: 'briefingsBody',
  search: 'searchBody',
  overview: 'overviewBody',
  breaking: 'breakingBody',
  conflicts: 'conflictsBody',
  brain: 'brainBody',
  intelligenceWeb: 'intelwebBody',
  markets: 'marketsBody',
  status: 'statusBody',
  settings: 'settingsBody',
  views: 'viewsBody',
  map: 'mapContainer',
  mapOps: 'mapOpsBody'
};

/* S7 — one active view renders at a time; each view is rendered on first
 * activation and re-rendered on state changes while active. */
const VIEW_RENDER = {
  dashboard: [['dashboard', 'renderDashboard']],
  alerts: [['alerts', 'renderAlerts']],
  timeline: [['timeline', 'renderTimeline']],
  briefings: [['briefings', 'renderBriefings']],
  search: [['views', 'renderViews'], ['search', 'renderSearch']],
  overview: [['overview']],
  breaking: [['breaking']],
  conflicts: [['conflicts']],
  brain: [['brain', 'renderIntelligenceBrain'], ['brainTimeline', 'renderBrainTimeline']],
  intelweb: [['intelligenceWeb', 'renderIntelligenceWeb']],
  map: [['map', 'renderMap'], ['map', 'renderMapOps']],
  markets: [['markets']],
  status: [['status', 'renderStatus']],
  settings: [['settings', 'renderSettings']]
};

function showModuleError(id, err) {
  const el = document.getElementById(id);
  if (!el) return;
  const message = String(err?.message || err || 'Module failed to load').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c] || c));
  el.innerHTML = `<div class="gp-state"><div class="gp-state-title">Temporarily unavailable</div><div>${message}</div></div>`;
}

function focusUniversalSearch() {
  try { showView('search'); } catch {}
  const go = (tries) => {
    const input = document.getElementById('universalSearch');
    if (input) { input.focus(); return; }
    if (tries > 0) setTimeout(() => go(tries - 1), 200);
  };
  go(6);
}

function setupSearchShortcut() {
  document.addEventListener('keydown', (event) => {
    if (event.defaultPrevented) return;
    const mod = event.ctrlKey || event.metaKey;
    const target = event.target;
    const typing = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable);
    if ((mod && (event.key === 'k' || event.key === 'K')) || (!mod && event.key === '/' && !typing)) {
      event.preventDefault();
      focusUniversalSearch();
    }
  });
}

function setupHeaderSearch() {
  const button = document.getElementById('gpHeaderSearch');
  if (button) button.addEventListener('click', focusUniversalSearch);
}

function readPrefs() {
  try {
    const raw = JSON.parse(localStorage.getItem('gp.prefs.v1') || '{}');
    return {
      autoRefresh: raw.autoRefresh !== false,
      intervalMin: [5, 10, 15, 30].includes(Number(raw.intervalMin)) ? Number(raw.intervalMin) : 5,
    };
  } catch { return { autoRefresh: true, intervalMin: 5 }; }
}

let refreshTimer = null;
function resetRefreshTimer() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  const prefs = readPrefs();
  if (!prefs.autoRefresh) return;
  refreshTimer = setInterval(() => {
    if (document.visibilityState === 'visible') {
      refresh(false).then(() => renderView(currentView() || 'dashboard')).catch(err => console.error('Refresh failed', err));
    }
  }, prefs.intervalMin * 60 * 1000);
}

async function loadModules() {
  const imports = {
    dashboard: './modules/dashboard.js',
    alerts: './modules/alerts.js',
    timeline: './modules/timeline.js',
    briefings: './modules/briefings.js',
    search: './modules/search.js',
    overview: './modules/overview.js',
    breaking: './modules/breaking.js',
    conflicts: './modules/conflicts.js',
    brain: './modules/intelligence-brain.js',
    brainTimeline: './modules/brain-timeline.js',
    intelligenceWeb: './modules/intelligence-web.js',
    markets: './modules/markets.js',
    status: './modules/status.js',
    settings: './modules/settings.js',
    views: './modules/views.js',
    map: './modules/map.js'
  };
  const jobs = [];
  for (const [name, path] of Object.entries(imports)) {
    jobs.push(import(path).then(
      mod => { modules[name] = mod; },
      err => {
        console.error(`Global Pulse module failed to import: ${name}`, err);
        showModuleError(targets[name], err);
      }
    ));
  }
  await Promise.all(jobs);
}

function safeRender(name, fnName) {
  const mod = modules[name];
  const fn = fnName || `render${name[0].toUpperCase()}${name.slice(1)}`;
  if (!mod || typeof mod[fn] !== 'function') return;
  try { mod[fn](); }
  catch (err) { console.error(`Global Pulse render failed: ${name}`, err); showModuleError(targets[name], err); }
}

function renderView(view) {
  for (const [name, fnName] of (VIEW_RENDER[view] || [])) safeRender(name, fnName);
}

function handleActivation(view) {
  if (view === 'map') {
    try { modules.map?.initMap?.(); } catch (err) { console.error('Map init failed', err); }
  }
  if (view === 'intelweb') {
    try { window.__gpLoadIntelWebFrame?.(); } catch {}
  }
  renderView(view);
  /* Leaflet canvases need a size revalidation after a hidden→visible switch. */
  if (view === 'map' || view === 'dashboard') {
    setTimeout(() => { try { window.dispatchEvent(new Event('resize')); } catch {} }, 80);
  }
}

async function refresh(force = false) {
  const core = await loadCoreData({force});
  const mapMod = modules.map;
  if (mapMod?.loadMapData) {
    try { await mapMod.loadMapData(); }
    catch (err) { console.error('Global Pulse map data refresh failed', err); showModuleError(targets.map, err); }
  }
  return core;
}

async function boot() {
  setupSearchShortcut();
  setupHeaderSearch();
  setupDrawer();
  onActivate(handleActivation);
  setupRouter();
  window.addEventListener('gp:prefs-changed', resetRefreshTimer);
  await loadModules();
  handleActivation(currentView() || 'dashboard');
  try { await refresh(true); }
  catch (err) { console.error('Global Pulse core data refresh failed', err); }
  renderView(currentView() || 'dashboard');
  subscribe(() => renderView(currentView() || 'dashboard'));
  resetRefreshTimer();
  window.addEventListener('online', () => refresh(true).then(() => renderView(currentView() || 'dashboard')).catch(err => console.error('Online refresh failed', err)));
}

boot().catch(err => {
  console.error('Global Pulse boot failed', err);
  Object.entries(targets).forEach(([name, id]) => {
    if (!modules[name]) showModuleError(id, err);
  });
});
