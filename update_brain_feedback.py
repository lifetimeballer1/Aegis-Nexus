#!/usr/bin/env python3
"""Detect Intelligence Brain coverage gaps and turn them into next-cycle feed targets.

This is a build-time feedback loop: it never fabricates intelligence. It only
inspects source-backed artifacts already produced by the pipeline and emits
search/feed targets for the next refresh cycle.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
BRAIN = DATA / "intelligence_brain.json"
ARTIFACTS = ("live_articles.json", "claims.json", "intelligence_assessment.json", "intelligence_graph.json", "snapshot.json")

TARGETS = {
    "United States": ["United States", "U.S.", "USA", "American", "Washington", "Pentagon", "White House"],
    "China": ["China", "Chinese", "Beijing", "PLA", "People's Liberation Army", "CCP"],
    "Russia": ["Russia", "Russian", "Moscow", "Kremlin"],
    "Europe": ["European Union", "EU", "NATO", "Germany", "France", "United Kingdom"],
    "Western Hemisphere security": ["SOUTHCOM", "Southern Command", "Caribbean", "Eastern Pacific", "Mexico", "Ecuador", "cartel", "narco-terrorism"],
}


def load(name: str):
    p = DATA / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def record_text(obj: object) -> str:
    if not isinstance(obj, dict):
        return ""
    fields = ("title", "headline", "summary", "description", "content", "detail", "name", "country", "location", "category", "type", "tags", "keywords", "actor", "actors", "organization", "organizations", "group", "assessment", "claim", "text")
    return " ".join(str(obj.get(k, "")) for k in fields).lower()


def main() -> None:
    brain = load("intelligence_brain.json") or {}
    nodes = brain.get("nodes") or []
    node_text = " ".join(record_text(n) for n in nodes)

    records = []
    for name in ARTIFACTS:
        obj = load(name)
        if obj is not None:
            records.extend(walk(obj))
    corpus = " ".join(record_text(r) for r in records)

    gaps = []
    targets = []
    for label, aliases in TARGETS.items():
        present_node = any(str(n.get("label", "")).strip().lower() == label.lower() for n in nodes if isinstance(n, dict))
        mentions = sum(1 for alias in aliases if re.search(r"(?<![a-z])" + re.escape(alias.lower()) + r"(?![a-z])", corpus))
        node_mentions = sum(1 for alias in aliases if re.search(r"(?<![a-z])" + re.escape(alias.lower()) + r"(?![a-z])", node_text))
        if not present_node or node_mentions < 2:
            gaps.append({"target": label, "reason": "insufficient canonical-node coverage despite source corpus mentions" if mentions else "no recent source-backed coverage detected"})
            query = " OR ".join(quote(a) for a in aliases[:5])
            targets.append({
                "name": f"Feedback — {label}",
                "url": f"https://news.google.com/rss/search?q={quote(query)}+when%3A24h&hl=en-US&gl=US&ceid=US:en",
                "type": "brain-feedback",
                "target": label,
            })

    payload = {
        "version": 1,
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourceBackedOnly": True,
        "brainNodes": len(nodes),
        "gaps": gaps,
        "feedTargets": targets,
        "policy": "Targets are derived from missing/weak source-backed coverage only. They are feed expansion hints, not intelligence claims.",
    }
    DATA.mkdir(exist_ok=True)
    (DATA / "brain_feedback.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"BRAIN FEEDBACK: gaps={len(gaps)} next-cycle feed targets={len(targets)}")


if __name__ == "__main__":
    main()
