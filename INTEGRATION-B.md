1. HEAD: `<link rel="stylesheet" href="css/track-b.css">` after intelweb-embed.css line.
2. TIMELINE TAB: in `#section-timeline .gp-section-body`, APPEND `partials/ctimeline.html`
3. fragment (`<div id="ctimelineBody">…`) AFTER existing `<div id="timelineBody">` — replace nothing.
4. BODY END: `<script type="module" src="js/modules/ctimeline.js"></script>` after app.js script.
5. No app.js edit needed: module auto-paints `#ctimelineBody` on DOMContentLoaded.
6. Optional: register `ctimeline: './modules/ctimeline.js'` + `safeRender('ctimeline')` (exports both casings).
7. DATA: section fetches `data/gui-fixtures.json` (frozen copy of `~/aegis-gui/fixtures.json`).
8. SCOPE: TRACK-B owns css/track-b.css, js/modules/ctimeline.js, partials/ctimeline.html only.
9. READ-ONLY borrowed: briefings.js/alerts.js/timeline.js patterns, tokens.css + gp-* primitives.
10. VERIFY: open #section-timeline → 4 headline cards, tension 41, mix bars, working alerts feed.
