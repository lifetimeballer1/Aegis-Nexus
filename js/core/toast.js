/** Global Pulse — toast queue (module).
 * Visual contract lives in css/components.css (.gp-toast-stack/.gp-toast).
 * Queue of max 3, aria-live polite, auto-dismiss 6s, manual close.
 * All motion is CSS-guarded (prefers-reduced-motion). No telemetry.
 */
const MAX_TOASTS = 3;
const DISMISS_MS = 6000;

function stack() {
  let el = document.querySelector('.gp-toast-stack');
  if (el) return el;
  el = document.createElement('div');
  el.className = 'gp-toast-stack';
  el.setAttribute('role', 'status');
  el.setAttribute('aria-live', 'polite');
  document.body.appendChild(el);
  return el;
}

const TYPES = ['info', 'success', 'warning', 'error'];

export function showToast(message, type = 'info') {
  const host = stack();
  const kind = TYPES.includes(type) ? type : 'info';
  while (host.children.length >= MAX_TOASTS) host.firstChild?.remove();
  const text = String(message ?? '').slice(0, 280);
  const toast = document.createElement('div');
  toast.className = `gp-toast${kind === 'info' ? '' : ` ${kind}`}`;
  toast.setAttribute('tabindex', '-1');
  const body = document.createElement('span');
  body.textContent = text;
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'gp-btn';
  close.style.cssText = 'margin-left:8px;padding:2px 8px;min-height:28px;font-size:11px';
  close.setAttribute('aria-label', 'Dismiss notification');
  close.textContent = 'Dismiss';
  let timer = null;
  const dismiss = () => {
    if (timer) clearTimeout(timer);
    toast.remove();
  };
  close.addEventListener('click', dismiss);
  toast.append(body, close);
  host.appendChild(toast);
  timer = setTimeout(dismiss, DISMISS_MS);
  return dismiss;
}

export function toastInfo(m) { return showToast(m, 'info'); }
export function toastSuccess(m) { return showToast(m, 'success'); }
export function toastWarning(m) { return showToast(m, 'warning'); }
export function toastError(m) { return showToast(m, 'error'); }
