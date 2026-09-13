# Track A Integration — GUI-1 Command Center + GUI-4 Map
1. CSS: add `<link rel="stylesheet" href="css/track-a.css">` after `css/command-shell.css` in index.html `<head>`.
2. CENTER: paste `partials/center.html` (`#trackA-center`) inside `#section-dashboard`, right after `<div id="dashboardBody">`.
3. MAP: paste `partials/cmap.html` (`#trackA-map`) inside `#section-map`, after `<div id="mapSidePanel">`.
4. JS: import `./modules/ccenter.js` (`TrackACenter.init`) + `./modules/cmap.js` (`TrackACmap.init`) after renderAll in app boot.
5. DATA: `data/gui-fixtures.json` (copy of `~/aegis-gui/fixtures.json`); fetch `data/gui-fixtures.json`; no live calls.
6. IDS owned: `#trackA-center`, `#trackA-map`; classes `ta-*`; never touch `index.html` shell, `dashboard.js`, B/C/D files.
7. VERIFY: `pytest tests/ -q` green; check 41/WATCH/735/80/31/9 + 58/64 + 6 drivers + 9 chips render.
8. A11Y: pills are tablist with arrow keys; `prefers-reduced-motion` disables ticks/anim; empty states if fetch fails.
9. ROLLBACK: remove the 2 sections + css link + 2 inits to revert Track A cleanly with zero side effects.
