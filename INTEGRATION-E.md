1. HEAD: `<link rel="stylesheet" href="css/track-e.css">` after track-d.css line.
2. BRIEFINGS TAB: create `#section-briefings` with `.gp-section-body`, PASTE `partials/briefs.html`
3. fragment (`<div id="cbriefsBody">…`) inside it — replace nothing.
4. BODY END: `<script type="module" src="js/modules/cbriefs.js"></script>` after app.js script.
5. No app.js edit needed: module auto-paints `#cbriefsBody` on DOMContentLoaded.
6. Optional: register `cbriefs: './modules/cbriefs.js'` + `safeRender('cbriefs')` (exports both casings).
7. DATA: cards from `data/gui-fixtures.json` headlines.stories + topDevelopments + events.
8. SCOPE: TRACK-E owns css/track-e.css, js/modules/cbriefs.js, partials/briefs.html only.
9. READ-ONLY borrowed: ctimeline.js thumb pattern, tokens.css + gp-* primitives.
10. VERIFY: open #section-briefings → brief cards w/ thumbs, te-search filters, details expand.
