# DESIGN BRIEF — Command-Center GUI + Skeleton (2026-09-11)

Boss: JaMichael. Worker: design bot on free EC2. Gate: NOTHING merges to
main without boss review. All work stays on `design/command-center`.

## Target look (refs 1–3: dark ops command-center)

- Dark base (near-black blues/grays), neon accents, white primary text.
- Left nav rail: icon + label items (Command, Alerts, Timeline, Briefings,
  Search, Map, Brain, Web, Markets, Sources, Settings).
- Modular panel grid: status overview, alerts queue with priority markers,
  news strip with headlines, market pulse, map ops.
- Top banner: live clock + date. Bottom status bar: Critical / Warning /
  Normal / OK states.
- Cyberpunk restraint: glow sparingly, hierarchy first, whitespace separates.
- Mobile (390px) stays first-class: capped labels/edges, centered, smooth.

## Scope order

1. GUI panels toward the target look (CSS + layout, index.html sections).
2. Skeleton underneath: section structure, nav wiring, panel data hooks.
3. Intel web 3D view keeps its abyss palette; fix label/edge anchoring
   so edges visibly terminate on nodes at all zooms.

## Hard rules (repo conventions)

- No new third-party deps, hosts, or CDN scripts.
- Every refresh artifact stays in the 12-file manifest gate; the
  update-snapshot workflow assertions must keep passing.
- Weak-edge hiding, viewport caps, and reduced-motion paths stay intact.
- Validators (`validate_*.py`, pytest) must pass before any merge request.
- Small commits, one concern each, messages say what changed and why.
