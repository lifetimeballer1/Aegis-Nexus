# INTEGRATION-F — Overview tab wiring (Track F, GUI Day2)
1. Partial: copy `partials/overview.html` inner `<section id="coverview">` into `#section-overview` in `index.html`.
2. CSS: add `<link rel="stylesheet" href="css/track-f.css">` after the `track-c.css` link in `<head>`.
3. JS: add `<script src="js/modules/coverview.js" defer></script>` with the other module scripts at end of `<body>`.
4. Init: auto-boots on `DOMContentLoaded` if `#coverview` exists; or call `Coverview.init("coverview")` manually.
5. Data: single source `fetch("data/gui-fixtures.json")`; no live-pipeline dependency, no imports.
6. Anchors: quick-nav cards are plain `href="#section-…"` links (dashboard/timeline/search/map/alerts/briefings) — no JS coupling.
7. Isolation: all CSS is `tf-*` namespaced, all JS state is IIFE-scoped (`window.Coverview` only); does not touch `app.js`.
8. Tests: suite `pytest tests/ -q` stays green — no existing file modified; stable `data-testid` hooks for future tests.
9. Mobile: mobile-first 390px base (2-col tiles/nav), `720px`/`1080px` widen; `prefers-reduced-motion` disables animation.
10. Verify: open `#section-overview`, confirm 6 tiles / tension bar / 4 headlines / 6 nav cards / freshness line render.
