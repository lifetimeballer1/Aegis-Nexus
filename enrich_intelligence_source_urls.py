#!/usr/bin/env python3
"""Restore canonical source URLs into Intelligence Web evidence after snapshot refresh."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SNAP = ROOT / "data" / "snapshot.json"
LIVE = ROOT / "data" / "live_articles.json"

def norm(v):
    return re.sub(r"\s+", " ", str(v or "").strip().lower())

def url_of(r):
    if not isinstance(r, dict):
        return ""
    credit = r.get("credit") or {}
    for key in ("original_link", "url", "sourceUrl", "source_url", "link"):
        v = r.get(key)
        if isinstance(v, str) and re.match(r"^https?://\S+$", v.strip(), re.I):
            return v.strip()
    v = credit.get("source_url") if isinstance(credit, dict) else ""
    return v.strip() if isinstance(v, str) and re.match(r"^https?://\S+$", v.strip(), re.I) else ""

def main():
    data = json.loads(SNAP.read_text(encoding="utf-8"))
    live = json.loads(LIVE.read_text(encoding="utf-8")) if LIVE.exists() else {}
    articles = live.get("articles", []) if isinstance(live, dict) else []
    by_title = {}
    by_source_title = {}
    for a in articles:
        if not isinstance(a, dict):
            continue
        u = url_of(a)
        t = norm(a.get("title"))
        s = norm(a.get("source") or a.get("sourceLabel") or a.get("publisher"))
        if u and t:
            by_title.setdefault(t, u)
            if s:
                by_source_title[(s, t)] = u

    graph = data.get("intelligenceGraph")
    if not isinstance(graph, dict):
        print("No Intelligence Web graph found; nothing to enrich")
        return

    changed = 0
    def enrich(ev):
        nonlocal changed
        if not isinstance(ev, dict):
            return
        if url_of(ev):
            if not ev.get("url"):
                ev["url"] = url_of(ev)
                changed += 1
            return
        t = norm(ev.get("title"))
        s = norm(ev.get("source"))
        u = by_source_title.get((s, t)) or by_title.get(t, "")
        if u:
            ev["url"] = u
            changed += 1

    for node in graph.get("nodes", []):
        for ev in node.get("evidence", []) if isinstance(node, dict) else []:
            enrich(ev)
    for edge in graph.get("edges", []):
        for ev in edge.get("evidence", []) if isinstance(edge, dict) else []:
            enrich(ev)

    if changed:
        SNAP.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Intelligence source URL enrichment: {changed} evidence records repaired")

if __name__ == "__main__":
    main()
