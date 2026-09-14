/** Phase 1 T2 — shared gp-drawer controller (vanilla, no deps).
 * Phone (<1024px): openDrawer(el) slides a .gp-drawer in from the right over
 * a tap-to-close scrim, locks body scroll, and moves focus into the drawer;
 * closeDrawer(el) reverses it and restores focus. Desktop (>=1024px): only
 * the .open marker class toggles — layout CSS leaves drawers in place, so
 * tabs render exactly as before. Close paths: [data-drawer-close] button
 * (delegated), scrim tap, Esc, right-swipe on the drawer. Call initDrawers()
 * once (idempotent); per-drawer cleanup via opts.onClose. */
export const PHONE_DRAWER_QUERY = '(max-width: 1023.98px)';

export function isPhoneDrawer() {
  try {
    return !!(window.matchMedia && window.matchMedia(PHONE_DRAWER_QUERY).matches);
  } catch { return true; }
}

let lastFocus = null;
const closeCbs = new WeakMap();

function scrim() {
  let s = document.getElementById('gpDrawerScrim');
  if (!s) {
    s = document.createElement('div');
    s.id = 'gpDrawerScrim';
    document.body.appendChild(s);
    s.addEventListener('click', () => closeAllDrawers());
  }
  return s;
}

function anyOpen() {
  return !!document.querySelector('.gp-drawer.open');
}

export function openDrawer(el, opts = {}) {
  if (!el) return false;
  /* Force reflow so a freshly rendered drawer still slides in. */
  try { void el.offsetWidth; } catch {}
  if (typeof opts.onClose === 'function') closeCbs.set(el, opts.onClose);
  el.classList.add('open');
  if (!isPhoneDrawer()) return true;
  try { scrim().classList.add('open'); } catch {}
  try { document.body.classList.add('gp-drawer-open'); } catch {}
  if (opts.stealFocus === false) return true;
  try {
    lastFocus = document.activeElement;
    if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
    const btn = el.querySelector('[data-drawer-close]');
    (btn || el).focus({ preventScroll: true });
  } catch {}
  return true;
}

export function closeDrawer(el, opts = {}) {
  if (!el) return;
  el.classList.remove('open');
  const cb = closeCbs.get(el);
  if (cb) {
    closeCbs.delete(el);
    if (!anyOpen()) {
      try { scrim().classList.remove('open'); } catch {}
      try { document.body.classList.remove('gp-drawer-open'); } catch {}
      try {
        if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
        lastFocus = null;
      } catch {}
    }
    if (opts.runCb !== false) {
      try { cb(); } catch (e) { console.error('drawer onClose failed', e); }
    }
    return;
  }
  if (!anyOpen()) {
    try { scrim().classList.remove('open'); } catch {}
    try { document.body.classList.remove('gp-drawer-open'); } catch {}
  }
}

export function closeAllDrawers() {
  document.querySelectorAll('.gp-drawer.open').forEach((el) => closeDrawer(el));
}

export function initDrawers() {
  if (initDrawers.done) return;
  initDrawers.done = true;
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && anyOpen()) closeAllDrawers();
  });
  document.addEventListener('click', (event) => {
    const btn = event.target && event.target.closest ? event.target.closest('[data-drawer-close]') : null;
    if (!btn) return;
    const host = btn.closest('.gp-drawer');
    if (host) closeDrawer(host);
  });
  /* Swipe-right-to-close (phone drawers slide in from the right). */
  let sx = 0, sy = 0, tracking = false;
  document.addEventListener('touchstart', (event) => {
    tracking = false;
    try {
      if (event.touches && event.touches.length === 1 && event.target && event.target.closest &&
          event.target.closest('.gp-drawer.open')) {
        sx = event.touches[0].clientX; sy = event.touches[0].clientY; tracking = true;
      }
    } catch {}
  }, { passive: true });
  document.addEventListener('touchend', (event) => {
    if (!tracking) return;
    tracking = false;
    try {
      const t = event.changedTouches && event.changedTouches[0];
      if (!t) return;
      const dx = t.clientX - sx, dy = t.clientY - sy;
      if (dx > 72 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        const host = event.target && event.target.closest ? event.target.closest('.gp-drawer.open') : null;
        if (host) closeDrawer(host);
      }
    } catch {}
  }, { passive: true });
}
