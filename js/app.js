/** Global Pulse — isolated application boot */
import { loadCoreData } from './core/fetch.js';
import { subscribe } from './core/state.js';
import { CONFIG } from './core/config.js';
import { setupDrawer } from './core/drawer.js';

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

function showModuleError(id, err) {
  const el = document.getElementById(id);
  if (!el) return;
  const message = String(err?.message || err || 'Module failed to load').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c] || c));
  el.innerHTML = `<div class="gp-state"><div class="gp-state-title">Temporarily unavailable</div><div>${message}</div></div>`;
}

function focusUniversalSearch() {
  const go = (tries) => {
    const input = document.getElementById('universalSearch');
    if (input) {
      try { document.getElementById('section-search')?.scrollIntoView({ block: 'start' }); } catch {}
      input.focus();
      return;
    }
    if (tries > 0) setTimeout(() => go(tries - 1), 300);
  };
  try { window.location.hash = '#section-search'; } catch {}
  go(4);
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
      refresh(false).then(renderAll).catch(err => console.error('Refresh failed', err));
    }
  }, prefs.intervalMin * 60 * 1000);
}
function setupNav() {
  const items = document.querySelectorAll('.gp-nav-item, .gp-rail-item');
  items.forEach(item => item.addEventListener('click', () => {
    items.forEach(i => i.classList.remove('active'));
    item.classList.add('active');
  }));
  if (typeof IntersectionObserver === 'undefined') return;
  const sections = document.querySelectorAll('[data-section]');
  const observer = new IntersectionObserver(entries => entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const id = entry.target.dataset.section;
    items.forEach(i => {
      const on = i.dataset.nav === id;
      i.classList.toggle('active', on);
      if (on) i.setAttribute('aria-current', 'true'); else i.removeAttribute('aria-current');
    });
  }), {threshold:.35});
  sections.forEach(s => observer.observe(s));
}

function setupHeaderSearch() {
  const button = document.getElementById('gpHeaderSearch');
  if (button) button.addEventListener('click', focusUniversalSearch);
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

function safeRender(name, fnName = `render${name[0].toUpperCase()}${name.slice(1)}`) {
  const mod = modules[name];
  if (!mod || typeof mod[fnName] !== 'function') return;
  try { mod[fnName](); }
  catch (err) { console.error(`Global Pulse render failed: ${name}`, err); showModuleError(targets[name], err); }
}

function renderAll() {
  safeRender('dashboard', 'renderDashboard');
  safeRender('alerts', 'renderAlerts');
  safeRender('timeline', 'renderTimeline');
  safeRender('briefings', 'renderBriefings');
  safeRender('search', 'renderSearch');
  safeRender('overview');
  safeRender('breaking');
  safeRender('conflicts');
  safeRender('brain', 'renderIntelligenceBrain');
  safeRender('brainTimeline', 'renderBrainTimeline');
  safeRender('intelligenceWeb', 'renderIntelligenceWeb');
  safeRender('markets');
  safeRender('status', 'renderStatus');
  safeRender('settings', 'renderSettings');
  safeRender('views', 'renderViews');
  safeRender('map');
  safeRender('map', 'renderMapOps');
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
  setupNav();
  setupSearchShortcut();
  setupHeaderSearch();
  setupDrawer();
  window.addEventListener('gp:prefs-changed', resetRefreshTimer);
  await loadModules();
  if (modules.map?.initMap) {
    try { modules.map.initMap(); } catch (err) { console.error('Map init failed', err); }
  }
  try { await refresh(true); }
  catch (err) { console.error('Global Pulse core data refresh failed', err); }
  renderAll();
  subscribe(() => renderAll());
  resetRefreshTimer();
  window.addEventListener('online', () => refresh(true).then(renderAll).catch(err => console.error('Online refresh failed', err)));
  setTimeout(() => {
    try { modules.map?.initMap?.(); modules.map?.renderMap?.(); }
    catch (err) { console.error('Map retry failed', err); }
  }, 1000);
}

boot().catch(err => {
  console.error('Global Pulse boot failed', err);
  Object.entries(targets).forEach(([name, id]) => {
    if (!modules[name]) showModuleError(id, err);
  });
});
