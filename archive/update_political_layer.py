#!/usr/bin/env python3
"""Promote politics/economics into explicit first-class story layers.

No API keys are required. Classification is deterministic and provenance-preserving:
feed labels are preferred, then conservative title/summary rules are used only as
fallbacks. Stories are never removed from the general feed.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / "data" / "snapshot.json"

US_POLITICS = re.compile(r"\b(trump|white house|congress|senate|house of representatives|supreme court|governor|midterm|election|primary|democrat|republican|gop|president|federal reserve nomination|cabinet|executive order)\b", re.I)
WORLD_POLITICS = re.compile(r"\b(president|prime minister|parliament|election|referendum|coalition|government|diplomacy|diplomatic|summit|treaty|alliance|sanction|sanctions|ceasefire talks|negotiations|envoy|foreign minister)\b", re.I)
ECONOMICS = re.compile(r"\b(oil|crude|natural gas|lng|inflation|tariff|tariffs|trade|exports?|imports?|stocks?|shares|bond yields?|treasury|currency|dollar|euro|yuan|yen|interest rate|central bank|gdp|economy|economic|commodity|commodities|shipping|freight|supply chain|opec)\b", re.I)
CONFLICT = re.compile(r"\b(war|conflict|military|troops|missile|drone|airstrike|shelling|offensive|insurgent|militant|clash|coup|cartel|gang|bombing|hostage)\b", re.I)


def classify(story):
    feed = str(story.get("category") or story.get("feedCategory") or story.get("topic") or "").lower()
    source = str(story.get("sourceLabel") or "").lower()
    blob = f"{story.get('title','')} {story.get('summary','')}"

    # Explicit feed routing always wins. This prevents broad GDELT/Reuters/etc.
    # stories from being misclassified by a single keyword.
    if "us-politics" in feed or "npr politics" in source:
        return "us-politics"
    if "world-politics" in feed:
        return "world-politics"
    if "economics" in feed:
        return "economics"

    # Conservative fallback: prefer a dedicated political/economic signal over
    # conflict language, but don't force a connection when evidence is absent.
    if US_POLITICS.search(blob) and not CONFLICT.search(blob):
        return "us-politics"
    if WORLD_POLITICS.search(blob) and not CONFLICT.search(blob):
        return "world-politics"
    if ECONOMICS.search(blob) and not CONFLICT.search(blob):
        return "economics"
    return "general"


def main():
    data = json.loads(SNAP.read_text(encoding="utf-8"))
    stories = data.get("stories", [])
    counts = {"us-politics": 0, "world-politics": 0, "economics": 0, "general": 0}
    for story in stories:
        layer = classify(story)
        story["intelligenceLayer"] = layer
        counts[layer] += 1

    # First-class arrays make the frontend independent of source ordering and
    # make the generated snapshot useful to other clients/API consumers.
    data["politics"] = [s for s in stories if s["intelligenceLayer"] in ("us-politics", "world-politics")]
    data["usPolitics"] = [s for s in stories if s["intelligenceLayer"] == "us-politics"]
    data["worldPolitics"] = [s for s in stories if s["intelligenceLayer"] == "world-politics"]
    data["economics"] = [s for s in stories if s["intelligenceLayer"] == "economics"]
    data["layerCounts"] = counts
    data["layerNote"] = "Political and economic layers use explicit feed provenance first, then conservative headline/summary classification. General stories remain independent unless evidence supports a relationship."
    SNAP.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("INTELLIGENCE LAYERS:", counts)


if __name__ == "__main__":
    main()
