# INTEGRATION-D — ALERTS tab wiring (builder D, 10 lines)
1. Paste `partials/alerts.html` inner `.td-wrap` into `#alertsBody` in `index.html` (replaces the loading spinner).
2. Add `<link rel="stylesheet" href="css/track-d.css">` in `<head>` after `track-c.css`.
3. Add `<script src="js/modules/calerts.js"></script>` with the other classic scripts (NOT a module; exposes `window.Calerts`).
4. No `app.js` change needed: `calerts.js` auto-inits on `DOMContentLoaded` when `#alertsBody` exists.
5. Manual re-init (if tab body is injected late): `window.Calerts.init('alertsBody')`.
6. Data: `fetch('data/gui-fixtures.json')` only — alerts block + headlines + meta.frozenAt; no live calls.
7. Filters ALL/CRITICAL/WATCH/INFO re-render client-side; counts in pills are real counts from the snapshot.
8. Retry re-fetches with 800ms→1.6s→3.2s backoff (3 attempts), status line narrates; never a dead button.
9. Test ids: `td-root/td-filters/td-filter-<all|critical|watch|info>/td-retry/td-status/td-list/td-card-<i>/td-empty/td-error`.
10. Conflicts with old `alerts.js`? None — `calerts.js` touches only `#alertsBody .td-*`; legacy module left intact.
