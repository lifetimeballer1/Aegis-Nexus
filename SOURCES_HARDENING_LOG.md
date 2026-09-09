# Sources/Pipeline Hardening — Progress Card (2026-09-09, hour grind)

HEAD base: 74a4ec6 (main, +2 unpushed). Data/artifacts owned by outside refresh — never staged.
Rule: commit ONLY scoped code files, never push. Pattern: `fix(sources): <batch>`.

## Live verification — resilient_feed_catalog.py (50 feeds, 2026-09-09)
- LIVE (39): GDACS, Fox Politics, BBC World/ME/Africa/Asia/Europe, Guardian World/US,
  NPR National Security (1122), Al Jazeera, DW, Crisis Group, GNews SOUTHCOM/JTFWH/
  ACCCounterCartel/US-CounterCartel/LosChoneros/SinaloaCJNG/Humanitarian/USPolitics/
  CNNPolitics/AxiosPolitics/GlobalEconomics/GlobalConflict/Sudan/DRC/Sahel/Haiti/
  Ecuador/Myanmar/Yemen/RedSea/IranIsrael/Ukraine/SouthAmerica/MEast/SouthAsia,
  France 24 endpoint noted below.
- DEAD (3): NPR News 1001 (flaky 404, works intermittently — retry covers),
  GDELT SOUTHCOM mirror 429, GDELT WHCC 429 (throttling — spacing+backoff covers).
- LIMITED-empty (9): Op Southern Spear, Climate&Disaster, ClimateSecurity,
  Morse Report, WorldPolitics, AfricaSecurity, SomaliaSecurity, MexicoCartel,
  AfghanistanSecurity — all narrow 6–8-term AND queries; broadened 2–4-term
  versions verified live with results (see Batch 2).
- France 24 https://www.france24.com/en/rss serves HTML (not RSS) — dead as RSS.
  Verified replacement: RFI English https://www.rfi.fr/en/general/rss (22 items,
  same France Médias Monde family). See Batch 2.

## Batches
- [x] Batch 1 — collector retry/backoff (news_feed_db.py): 429/5xx retries w/
      backoff (2/8/20s), GDELT spacing >=2.5s (thread-safe), per-source timeouts
      (GDELT 25s/NPR 15s/default 12s), HTML-payload guard, limits documented.
      Verified: import ok, behavior probes ok, source-health PASS, pytest 123 passed.
- [ ] Batch 2 — catalog fixes (resilient_feed_catalog.py + update_snapshot.py):
      France24→RFI replacement, broaden 9 narrow queries (verified live).
- [ ] Batch 3 — quarantine mapping + fallbacks (source_failover.py,
      build_source_health.py): documented quarantine table, X-proxy note.
- [ ] Batch 4 — manifest freshness + source-health thresholds review.
- [ ] Final — full validator sweep (12/12), pytest, diff check, report.
