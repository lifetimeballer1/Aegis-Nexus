/** App shell view router (S1-S4).
 * Hash routes remain #section-<id> so every existing deep link and test anchor
 * keeps working. One view is active at a time; navigation elements stay in sync
 * across command tabs, rail and mobile tabs. Record hashes (QA deep links) are
 * passed through untouched. */

const VIEWS = ['dashboard', 'alerts', 'timeline', 'briefings', 'search', 'overview', 'breaking', 'conflicts', 'brain', 'intelweb', 'map', 'markets', 'status', 'settings'];
const REDIRECTS = { overview: 'dashboard' };

let current = null;
const activations = [];

export function onActivate(fn) {
  if (typeof fn === 'function') activations.push(fn);
}

export function currentView() {
  return current;
}

export function viewSections() {
  return VIEWS.slice();
}

function syncNav(view) {
  document.querySelectorAll('.gp-nav-item, .gp-rail-item').forEach(el => {
    const on = el.dataset.nav === view;
    el.classList.toggle('active', on);
    if (on) el.setAttribute('aria-current', 'page');
    else el.removeAttribute('aria-current');
  });
}

export function showView(view, { push = true } = {}) {
  const target = REDIRECTS[view] || view;
  if (!VIEWS.includes(target)) return false;
  const section = document.getElementById('section-' + target);
  if (!section) return false;
  if (current === target) {
    document.getElementById('gpMoreSheet')?.classList.remove('open');
    return true;
  }
  document.body.setAttribute('data-view', target);
  document.querySelectorAll('[data-section]').forEach(s => s.classList.toggle('view-active', s === section));
  syncNav(target);
  current = target;
  if (push) {
    const hash = '#section-' + target;
    if (location.hash !== hash) {
      try { history.pushState(null, '', hash); } catch { location.hash = hash; }
    }
  }
  try { window.scrollTo({ top: 0 }); } catch {}
  document.getElementById('gpMoreSheet')?.classList.remove('open');
  for (const fn of activations) {
    try { fn(target); } catch (err) { console.error('View activation failed', target, err); }
  }
  return true;
}

function routeFromHash() {
  const raw = String(location.hash || '').replace(/^#/, '');
  const match = /^section-([a-z-]+)$/.exec(raw);
  if (!match) return;
  showView(match[1], { push: false });
}

export function setupRouter() {
  document.addEventListener('click', event => {
    const toggle = event.target.closest?.('[data-more-toggle]');
    if (toggle) {
      event.preventDefault();
      const sheet = document.getElementById('gpMoreSheet');
      if (sheet) {
        const open = sheet.classList.toggle('open');
        toggle.setAttribute('aria-expanded', String(open));
      }
      return;
    }
    const anchor = event.target.closest?.('a[href^="#section-"]');
    if (!anchor) return;
    const view = String(anchor.getAttribute('href') || '').replace('#section-', '');
    if (!VIEWS.includes(view)) return;
    event.preventDefault();
    showView(view);
  });
  window.addEventListener('hashchange', routeFromHash);
  window.addEventListener('popstate', routeFromHash);
  routeFromHash();
  if (!current) showView('dashboard', { push: false });
}
