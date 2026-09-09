#!/usr/bin/env python3
"""Validate the CURRENT live collector result before publication.

The collector intentionally includes optional search/social feeds. A transient
failure in several optional feeds must not block the entire publication when
there are still enough healthy sources, fresh rows, and required coverage.

Threshold rationale (reviewed 2026-09-09, still meaningful after the feed
fixes — bounds stay loose on purpose so transient GDELT 429 windows and
flaky NPR 404s never block publication, while a real systemic outage trips
multiple bounds at once):
- MIN_FEEDS=20: registry carries ~50 catalog + ~14 collector-builtin feeds;
  20 means more than two-thirds of polling vanished before we block.
- MIN_ROWS=1: any fetched row proves the collector pipeline moved data;
  row volume is monitored via telemetry, not gated, because GDELT
  throttling windows can crater volume transiently.
- MIN_HEALTHY_SOURCES=20 / MIN_HEALTHY_RATIO=0.40 / MAX_FAILURE_RATIO=0.60:
  steady state is ~56/65 healthy (86%); the 5 quarantined X proxies alone
  can never trip these bounds, but a systemic outage (e.g. all Google News
  or all GDELT failing) trips all three together.
- REQUIRED_CATEGORIES (international, us-politics, security): each is backed
  by several independent publishers, so an uncovered category means a whole
  brief section lost its sourcing, not one feed blinking.
- REQUIRED_COVERAGE united-states/china x MIN_COVERAGE_SOURCES=2: the two
  major-power briefs each need at least two usable sources with actual rows.
"""
from __future__ import annotations
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
STATUS = DATA / "live_status.json"
MIN_FEEDS = 20
MIN_ROWS = 1
MIN_HEALTHY_RATIO = 0.40
MAX_FAILURE_RATIO = 0.60
MIN_HEALTHY_SOURCES = 20
REQUIRED_CATEGORIES = {"international", "us-politics", "security"}
REQUIRED_COVERAGE = {"united-states", "china"}
MIN_COVERAGE_SOURCES = 2
USABLE_MODES = {"native", "gdelt-domain-fallback"}


def main() -> int:
    if not STATUS.is_file() or STATUS.stat().st_size == 0:
        raise SystemExit("SOURCE HEALTH GATE FAILED: live_status.json missing/empty")
    d = json.loads(STATUS.read_text(encoding="utf-8"))
    feeds = int(d.get("feedsChecked") or 0)
    rows = int(d.get("rowsFetched") or 0)
    results = d.get("sourceResults") or []
    if feeds < MIN_FEEDS or rows < MIN_ROWS:
        raise SystemExit(f"SOURCE HEALTH GATE FAILED: feeds={feeds}, rows={rows}")
    if not isinstance(results, list) or not results:
        raise SystemExit("SOURCE HEALTH GATE FAILED: no current source results")

    total = len(results)
    healthy = sum(1 for s in results if s.get("httpOk") is True)
    failed = sum(1 for s in results if s.get("httpOk") is not True)
    healthy_ratio = healthy / total
    failure_ratio = failed / total
    if healthy < MIN_HEALTHY_SOURCES:
        raise SystemExit(f"SOURCE HEALTH GATE FAILED: healthy sources={healthy} < {MIN_HEALTHY_SOURCES}")
    if healthy_ratio < MIN_HEALTHY_RATIO:
        raise SystemExit(f"SOURCE HEALTH GATE FAILED: current healthy ratio={healthy_ratio:.1%} < {MIN_HEALTHY_RATIO:.0%}")
    if failure_ratio > MAX_FAILURE_RATIO:
        raise SystemExit(f"SOURCE HEALTH GATE FAILED: current failure ratio={failure_ratio:.1%} > {MAX_FAILURE_RATIO:.0%}")

    uncovered = []
    for category in REQUIRED_CATEGORIES:
        candidates = [s for s in results if s.get("category") == category]
        usable = [s for s in candidates if s.get("httpOk") is True and s.get("mode") in USABLE_MODES]
        if not usable:
            uncovered.append(category)
    if uncovered:
        raise SystemExit("SOURCE HEALTH GATE FAILED: no usable current source for " + ", ".join(sorted(uncovered)))

    missing_coverage = []
    coverage_report = {}
    for coverage in REQUIRED_COVERAGE:
        candidates = [s for s in results if coverage in (s.get("coverage") or [])]
        usable = [s for s in candidates if s.get("httpOk") is True and s.get("mode") in USABLE_MODES and s.get("rowsFetched", 0) > 0]
        coverage_report[coverage] = len(usable)
        if len(usable) < MIN_COVERAGE_SOURCES:
            missing_coverage.append(f"{coverage} ({len(usable)} usable sources)")
    if missing_coverage:
        raise SystemExit("SOURCE HEALTH GATE FAILED: strategic coverage below minimum: " + ", ".join(sorted(missing_coverage)))

    fallback = sum(1 for s in results if s.get("mode") == "gdelt-domain-fallback")
    empty = sum(1 for s in results if s.get("httpOk") is True and s.get("emptyFeed") is True)
    print("PASS: current source health gate")
    print(f"feeds={feeds} results={total} rows={rows} healthy={healthy}/{total} ({healthy_ratio:.1%}) failed={failed} ({failure_ratio:.1%})")
    print(f"empty={empty} gdeltFallback={fallback} required-categories={','.join(sorted(REQUIRED_CATEGORIES))}")
    print("strategic-coverage=" + ", ".join(f"{k}:{v}" for k,v in sorted(coverage_report.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
