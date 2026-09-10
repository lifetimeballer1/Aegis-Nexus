/** Shared reading-pane drawer (Concept 05).
 * Device-local presentation only: renders analyst-provided markup that the
 * caller has already escaped. No data is generated here. */

let lastFocus = null;

function nodes() {
  return {
    drawer: document.getElementById('gpDrawer'),
    scrim: document.getElementById('gpDrawerScrim'),
    title: document.getElementById('gpDrawerTitle'),
    body: document.getElementById('gpDrawerBody')
  };
}

export function openDrawer({ title, html } = {}) {
  const { drawer, scrim, title: titleEl, body } = nodes();
  if (!drawer || !scrim || !body) return;
  lastFocus = document.activeElement;
  if (titleEl) titleEl.textContent = String(title || 'Details');
  body.innerHTML = String(html || '');
  scrim.classList.add('open');
  drawer.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  drawer.querySelector('.gp-drawer-close')?.focus();
}

export function closeDrawer() {
  const { drawer, scrim } = nodes();
  if (!drawer || !scrim) return;
  scrim.classList.remove('open');
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  if (lastFocus && typeof lastFocus.focus === 'function') {
    try { lastFocus.focus(); } catch {}
  }
  lastFocus = null;
}

export function setupDrawer() {
  const { drawer, scrim } = nodes();
  if (!drawer || !scrim) return;
  document.getElementById('gpDrawerClose')?.addEventListener('click', closeDrawer);
  scrim.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && drawer.classList.contains('open')) closeDrawer();
  });
}
