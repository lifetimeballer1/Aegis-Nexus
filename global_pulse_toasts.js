/* Global Pulse — toast queue (global fallback for non-module contexts).
 * Visual contract: css/components.css (.gp-toast-stack/.gp-toast).
 * Exposes window.gpToast(message, type). Max 3, aria-live polite,
 * auto-dismiss 6s, manual Dismiss button. No network, no telemetry.
 */
(function () {
  'use strict';
  if (window.gpToast) return;
  var MAX = 3, DISMISS_MS = 6000;
  function stack() {
    var el = document.querySelector('.gp-toast-stack');
    if (el) return el;
    el = document.createElement('div');
    el.className = 'gp-toast-stack';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    document.body.appendChild(el);
    return el;
  }
  window.gpToast = function (message, type) {
    var host = stack();
    var kind = ['success', 'warning', 'error'].indexOf(type) >= 0 ? type : 'info';
    while (host.children.length >= MAX && host.firstChild) host.removeChild(host.firstChild);
    var text = String(message == null ? '' : message).slice(0, 280);
    var toast = document.createElement('div');
    toast.className = kind === 'info' ? 'gp-toast' : 'gp-toast ' + kind;
    toast.setAttribute('tabindex', '-1');
    var body = document.createElement('span');
    body.textContent = text;
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'gp-btn';
    close.style.cssText = 'margin-left:8px;padding:2px 8px;min-height:28px;font-size:11px';
    close.setAttribute('aria-label', 'Dismiss notification');
    close.textContent = 'Dismiss';
    var timer = null;
    var dismiss = function () { if (timer) clearTimeout(timer); if (toast.parentNode) toast.parentNode.removeChild(toast); };
    if (close.addEventListener) close.addEventListener('click', dismiss);
    else close.attachEvent('onclick', dismiss);
    toast.appendChild(body);
    toast.appendChild(close);
    host.appendChild(toast);
    timer = setTimeout(dismiss, DISMISS_MS);
    return dismiss;
  };
})();
