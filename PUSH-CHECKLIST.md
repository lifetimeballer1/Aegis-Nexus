# PUSH CHECKLIST — BLOCK 2 Integration (human runs from PC, GitHub creds live there)

Box aegis-burst has NO GitHub creds — NEVER push from the box.
Expected stack: 7 ahead of origin/main (2 pipeline + 5 gui).

  46a8105 pipeline: wire source_failover after failover-state refresh
  a907726 gui: dedupe commandStatusBar, CC-SHELL 01/05/06 skeleton dark
  f59a7c9 Track A GUI-1 command center + GUI-4 map
  b580b2e gui-3: network graph track-C
  536146c track-b: fixtures-backed command timeline
  e4305d9 track-b: INTEGRATION-B note
  <HASH> integrate: stitch 4 GUI sections (A/B/C) into index.html

NOTE 2026-09-13: box fetched origin/main during integration and sees
behind ~58 (GitHub main moved). Pull latest before merging.

## 1. From PC (PowerShell), bundle the box commits over Tailscale

  ssh -i $env:USERPROFILE\.ssh\ec2-helper ubuntu@100.94.80.109 "cd ~/Aegis-Nexus-B && git log --oneline origin/main..main && git bundle create /tmp/aegis-block2.bundle origin/main..main && git bundle verify /tmp/aegis-block2.bundle"

  scp -i $env:USERPROFILE\.ssh\ec2-helper ubuntu@100.94.80.109:/tmp/aegis-block2.bundle $env:TEMP\aegis-block2.bundle

## 2. In your PC clone of Aegis-Nexus (clone first if needed)

  git clone https://github.com/lifetimeballer1/Aegis-Nexus.git
  cd Aegis-Nexus
  git bundle verify $env:TEMP\aegis-block2.bundle
  git fetch $env:TEMP\aegis-block2.bundle main:burst-block2
  git checkout main
  git pull origin main
  git log --oneline main..burst-block2
  git diff main..burst-block2 --stat

## 3. Pre-push sanity (must all pass)

  git checkout burst-block2
  python -m pytest tests/ -q
  python -m http.server 8765
  browse http://127.0.0.1:8765/index.html — check Command / Timeline / Search / Map tabs, then Ctrl+C to stop the server

## 4. Merge and push (plain merge, NOT ff-only — main has moved)

  git checkout main
  git merge burst-block2 -m "merge: BLOCK 2 GUI integration from aegis-burst"
  python -m pytest tests/ -q
  git push origin main
  git branch -d burst-block2

## 5. After push — confirm box sees it (optional)

  ssh -i $env:USERPROFILE\.ssh\ec2-helper ubuntu@100.94.80.109 "cd ~/Aegis-Nexus-B && git fetch origin && git status -sb"

## LEFT ON BOX INTENTIONALLY (NOT in bundle — uncommitted / untracked)

- M data/snapshot.json — live refresh artifact, regenerates on next run
- WORKER-B-SUMMARY.md, tests/test_gui_phase11_refs.py — other worker files, not mine
- ~/fleet-B ~/fleet-C ~/fleet-D — untouched per orders
