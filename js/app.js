/** Global Pulse — isolated application boot */
import { loadCoreData } from './core/fetch.js';
import { subscribe } from './core/state.js';
import { CONFIG } from './core/config.js';

const modules = {};
const targets = {
  dashboard: 'dashboardBody',
  alerts: 'alertsBody',
  timeline: 'timelineBody',
  overview: 'overviewBody',
  breaking: 'breakingBody',
  conflicts: 'conflictsBody',
  brain: 'brainBody',
  intelligenceWeb: 'intelweb',
  markets: 'marketsBody',
  status: 'statusBody',
  map: 'mapContainer'
};

function showModuleError(id, err) {
  const el = document.getElementById(id);
  if (!el) return;
  const message = String(err?.message || err || 'Module failed to load').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c] || c));
  el.innerHTML = `<div class="gp-state"><div class="gp-state-title">Temporarily unavailable</div><div>${message}</div></div>`;
}

function setupNav() {
  const items = document.querySelectorAll('.gp-nav-item');
  items.forEach(item => item.addEventListener('click', () => {
    items.forEach(i => i.classList.remove('active'));
    item.classList.add('active');
  }));
  if (typeof IntersectionObserver === 'undefined') return;
  const sections = document.querySelectorAll('[data-section]');
  const observer = new IntersectionObserver(entries => entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const id = entry.target.dataset.section;
    items.forEach(i => i.classList.toggle('active', i.dataset.nav === id));
  }), {threshold:.35});
  sections.forEach(s => observer.observe(s));
}

async function loadModules() {
  const imports = {
    dashboard: './modules/dashboard.js',
    alerts: './modules/alerts.js',
    timeline: './modules/timeline.js',
    overview: './modules/overview.js',
    breaking: './modules/breaking.js',
    conflicts: './modules/conflicts.js',
    brain: './modules/intelligence-brain.js',
    brainTimeline: './modules/brain-timeline.js',
    intelligenceWeb: './modules/intelligence-web.js',
    markets: './modules/markets.js',
    status: './modules/status.js',
    map: './modules/map.js'
  };
  for (const [name, path] of Object.entries(imports)) {
    try {
      modules[name] = await import(path);
    } catch (err) {
      console.error(`Global Pulse module failed to import: ${name}`, err);
      showModuleError(targets[name], err);
    }
  }
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
  safeRender('overview');
  safeRender('breaking');
  safeRender('conflicts');
  safeRender('brain', 'renderIntelligenceBrain');
  safeRender('brainTimeline', 'renderBrainTimeline');
  safeRender('intelligenceWeb', 'renderIntelligenceWeb');
  safeRender('markets');
  safeRender('status');
  safeRender('map');
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
  await loadModules();
  if (modules.map?.initMap) {
    try { modules.map.initMap(); } catch (err) { console.error('Map init failed', err); }
  }
  try { await refresh(true); }
  catch (err) { console.error('Global Pulse core data refresh failed', err); }
  renderAll();
  subscribe(() => renderAll());
  setInterval(() => {
    if (document.visibilityState === 'visible') {
      refresh(false).then(renderAll).catch(err => console.error('Refresh failed', err));
    }
  }, CONFIG.refresh.snapshot);
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
