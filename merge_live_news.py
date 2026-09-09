#!/usr/bin/env python3
"""Merge the persistent live-news database export into the public snapshot."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SNAP = DATA / "snapshot.json"
LIVE = DATA / "live_articles.json"
STATUS = DATA / "live_status.json"


def parse_time(value):
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        dt = parsedate_to_datetime(str(value))
    except Exception:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def canonical_time(value):
    """Return a browser-safe UTC ISO-8601 timestamp, or None if invalid."""
    if not value:
        return None
    dt = parse_time(value)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return None
    return dt.isoformat().replace("+00:00", "Z")


def normalize_article(item):
    """Return the canonical story shape consumed by the browser renderers."""
    url = item.get("url") or item.get("link") or item.get("sourceUrl")
    if not url:
        return None
    raw_published = item.get("published_date") or item.get("publishedDate") or item.get("time")
    published = canonical_time(raw_published)
    if not published:
        return None
    source = item.get("source") or item.get("source_name") or item.get("sourceLabel") or "Live source"
    title = item.get("title") or (f"Tweet by @{item.get('username')}" if item.get("username") else f"Update from {source}")
    summary = item.get("summary_snippet") or item.get("summary") or ""
    breaking_terms = ("strike", "attack", "killed", "drone", "missile", "blockade", "escalat", "invasion", "ceasefire", "bomb", "shell", "offensive", "coup", "clash", "shooting", "airstrike")
    blob = f"{title} {summary}".lower()
    breaking = bool(item.get("breaking")) or any(term in blob for term in breaking_terms)
    credit = item.get("credit") or item.get("credit_metadata") or {}
    # Preserve the exact source timestamp for the legacy news-feed contract;
    # non-news inputs continue to use the canonical UTC browser timestamp.
    browser_published = str(raw_published) if item.get("source_type") == "news" else published
    return {
        "id": hashlib.sha1(str(url).encode("utf-8")).hexdigest()[:12],
        "sourceLabel": source,
        "sourceName": source,
        "sourceType": item.get("sourceType") or item.get("source_type") or "live-rss",
        "title": str(title)[:240],
        "summary": str(summary)[:420],
        "summary_snippet": str(summary)[:420],
        "source": url,
        "url": url,
        "time": browser_published,
        "published_date": browser_published,
        "publishedDate": browser_published,
        "tag": "Breaking" if breaking else "World",
        "confidence": "DEVELOPING",
        "breaking": breaking,
        "liveDatabase": True,
        "credit": credit,
    }


def main():
    if not SNAP.exists() or not LIVE.exists():
        raise RuntimeError("live merge requires snapshot.json and live_articles.json")
    snapshot = json.loads(SNAP.read_text(encoding="utf-8"))
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    existing = {}
    dropped_invalid_timestamps = 0
    for story in snapshot.get("stories", []):
        normalized = normalize_article(story)
        if normalized:
            existing[normalized["url"]] = {**story, **normalized}
        else:
            dropped_invalid_timestamps += 1

    added = 0
    for item in live.get("articles", []):
        story = normalize_article(item)
        if not story or story["url"] in existing:
            continue
        existing[story["url"]] = story
        added += 1

    stories = sorted(existing.values(), key=lambda s: parse_time(s.get("time") or s.get("published_date")), reverse=True)[:300]
    snapshot["stories"] = stories

    import update_snapshot as base
    import update_snapshot_fast as builder
    from counter_cartel_runtime import install
    install(base, builder)
    previous = {"conflicts": snapshot.get("conflicts", [])}
    snapshot["conflicts"] = base.make_conflicts(stories, previous)

    now = datetime.now(timezone.utc).isoformat()
    snapshot["updatedAt"] = now
    snapshot["lastSuccessfulRefresh"] = now
    live_status = {}
    if STATUS.exists():
        try:
            live_status = json.loads(STATUS.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"live status parse warning: {type(exc).__name__}: {exc}")
    snapshot["liveDatabase"] = {
        "enabled": True,
        "articleCount": int(live.get("count", 0)),
        "lastExport": live.get("updatedAt"),
        "retentionDays": live.get("retentionDays", 7),
        "newMergedThisRun": added,
        "droppedInvalidTimestamps": dropped_invalid_timestamps,
    }
    feeds_checked = int(live_status.get("feedsChecked", 0))
    failed = len(live_status.get("failedSources", []))
    snapshot["failoverState"] = {
        "updatedAt": now,
        "total": feeds_checked,
        "down": failed,
        "healthy": max(0, feeds_checked - failed),
        "fallbacks": int(live_status.get("fallbackSources", 0)),
    }
    snapshot["sourceStatus"] = f"{len(stories)} stories · {added} live-db merged · persistent 7-day SQLite collector active"
    SNAP.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"live merge: {added} new rows, {len(stories)} total stories, droppedInvalidTimestamps={dropped_invalid_timestamps}")


if __name__ == "__main__":
    main()
