#!/usr/bin/env python3
"""Rebuild the feed registry (data/sources.json) from the canonical catalog.

sources.json drifted days behind the collector because nothing in the
canonical pipeline rewrote it. This step regenerates it every refresh from
resilient_feed_catalog.FEEDS in the exact shape news_feed_db.load_sources
expects ({updatedAt, feeds:[{name,url,type,domain}], errors:[]}).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def main() -> int:
    from resilient_feed_catalog import FEEDS

    seen: set[str] = set()
    feeds = []
    for entry in FEEDS:
        try:
            name, url = str(entry[0]).strip(), str(entry[1]).strip()
        except Exception:
            continue
        kind = str(entry[2]).strip() if len(entry) > 2 and entry[2] else "news"
        if not name or not url or url in seen:
            continue
        seen.add(url)
        feeds.append({"name": name, "url": url, "type": kind, "domain": urlparse(url).netloc})
    doc = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "feeds": feeds,
        "errors": [],
    }
    (DATA / "sources.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"SOURCES REGISTRY: {len(feeds)} feeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
