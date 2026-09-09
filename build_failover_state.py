#!/usr/bin/env python3
"""Refresh the snapshot failover-state block from current collector telemetry.

Preservation in this pipeline is retention-based (news_feed_db SQLite plus
retained export), not story merging: this step records WHAT the collector
saw (totals, failures, live GDELT fallback usage) without fetching or
injecting stories. Shape matches what validate_data_resilience requires
(sourceFailover.replacements list + failoverState counts); snapshot.updatedAt
is never touched here. The legacy Google-News merge path in
source_failover.py stays offline.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    live = json.loads((DATA / "live_status.json").read_text(encoding="utf-8"))
    snap_path = DATA / "snapshot.json"
    snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
    results = live.get("sourceResults") or []
    total = int(live.get("feedsChecked") or len(results))
    failed_sources = sorted({str(r.get("name") or r.get("sourceId")) for r in results if isinstance(r, dict) and r.get("httpOk") is not True})
    down = len(failed_sources)
    fallbacks = sum(1 for r in results if isinstance(r, dict) and r.get("mode") == "gdelt-domain-fallback")
    now = utcnow()
    snapshot["sourceFailover"] = {
        "updatedAt": now,
        "mode": "retained-cache",
        "note": "Retention-based preservation; no fallback stories merged.",
        "replacements": [],
    }
    snapshot["failoverState"] = {
        "updatedAt": now,
        "total": total,
        "down": down,
        "healthy": max(0, total - down),
        "fallbacks": fallbacks,
        "failedSources": failed_sources,
    }
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(f"FAILOVER STATE: total={total} down={down} fallbacks={fallbacks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
