# INTEGRATION-C — GUI-3 Network Graph (builder C)
1. Paste partials/cgraph.html section#section-cgraph into index.html inside #searchBody (SEARCH tab).
2. Add link css/track-c.css to head; import initCgraph from js/modules/cgraph.js as a module; call initCgraph().
3. Section fetches data/gui-fixtures.json (frozen copy of ~/aegis-gui/fixtures.json); no live pipeline calls.
4. Canvas lazy-renders via IntersectionObserver; static SVG fallback if canvas is unavailable; honors reduced-motion.
5. Windows ALL/24H/7D/30D/90D scale deterministically: x1.0/x0.18/x0.45/x0.75/x1.0 on hash-sorted node slice plus hub counts.
6. OPEN FILTERS drawer holds source checkboxes, category select, min-reports 0-5 slider; cards show outlet/time/category/link.
7. Perf: nodes capped 120, edges capped 300, DPR at most 2, one rAF loop paused offscreen; 390px mobile-first layout.
8. Owned files only: css/track-c.css, js/modules/cgraph.js, partials/cgraph.html, data/gui-fixtures.json, INTEGRATION-C.md.
9. Verify: pytest tests/ -q stays green; open SEARCH tab, scroll graph into view, exercise pills and filters.
