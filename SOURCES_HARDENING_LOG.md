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
- [x] Batch 2 — catalog fixes (resilient_feed_catalog.py, news_feed_db.py
      builtin, update_snapshot.py legacy list): France24→RFI World replacement
      (https://www.rfi.fr/en/general/rss, 22 items live, same media group);
      broadened 9 zero-result queries (all verified live w/ results: 4/11/58/
      3/9/5/11/5/97 items); removed duplicate France 24 builtin so the registry
      is the single source of truth.
      Verified: catalog shape (50 feeds, no dup names), each changed URL live,
      source-health PASS, resilience PASS, pipeline PASS, repo PASS, pytest 123.
- [x] Batch 3 — quarantine mapping + fallbacks (source_failover.py,
      build_source_health.py): QUARANTINE table (France24→RFI replaced; 5 X
      proxies unavailable-documented; NPR/GDELT retry-covered, not quarantined);
      CURRENT_FALLBACKS keyed to live failing GDELT-mirror names so fallback
      discovery actually triggers; quarantine doc entries appended to
      replacements[] with shapes preserved; health telemetry gains additive
      quarantined/quarantineNote flags (thresholds untouched).
      Verified: all 8 published failures covered (6 docs + 2 fallback paths),
      source-health PASS, resilience PASS, pytest 123 passed.
- [x] Batch 4 — manifest freshness + thresholds (build_validation_results.py,
      validate_source_health.py): manifest annotation (generatedAt/ageSeconds/
      stale>7200s) added, 12 contracts untouched; hash gate proven live (12/12
      artifact hashes match — any drift fails the gate); threshold rationale
      documented in-gate, numbers unchanged (bounds loose by design, systemic
      outages still trip multiple bounds).
      Verified: hash-match probe, annotation import check, resilience+manifest
      PASS, source-health PASS, pytest 123 passed.
- [x] Loop-back (second live pass: 48/50 LIVE, 0 limited, 2 GDELT 429) —
      batch 5 (resilient_feed_catalog.py, news_feed_db.py): WHCC GDELT query
      lightened maxrecords 250→100 (collector parses max 100) + window
      15m→30m; hardened fetch() recovered SOUTHCOM mirror live (HTTP 200
      after backoff, 25s); empty-body 200s now raise a clear ValueError
      instead of a cryptic XML ParseError for triage.
      Verified: error-message probes, source-health PASS, manifest PASS,
      pytest 123 passed.
- [ ] Final — full validator sweep (12/12), pytest, diff check, report.
