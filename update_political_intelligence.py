#!/usr/bin/env python3
"""Build an automatic, provenance-first political intelligence layer.

Deterministic and conservative: clusters similar reports, counts independent
source domains, extracts issue/entity signals, and labels corroboration only
when independent domains report a sufficiently similar event in a limited window.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / "data" / "snapshot.json"

ENTITY_PATTERNS = {
    "Donald Trump": r"\btrump\b|\bdonald trump\b|\bpresident trump\b",
    "White House": r"\bwhite house\b",
    "Congress": r"\bcongress\b|\bhouse of representatives\b",
    "U.S. Senate": r"\bsenate\b|\bsenator\b",
    "Supreme Court": r"\bsupreme court\b|\bscotus\b",
    "Democrats": r"\bdemocrat\w*\b|\bdemocratic party\b",
    "Republicans": r"\brepublican\w*\b|\bgop\b",
    "Federal Reserve": r"\bfederal reserve\b|\bfed\b",
    "Department of Justice": r"\bdepartment of justice\b|\bdoj\b",
    "China": r"\bchina\b|\bchinese\b|\bbeijing\b",
    "Russia": r"\brussia\b|\brussian\b|\bmoscow\b|\bputin\b",
    "Ukraine": r"\bukraine\b|\bukrainian\b|\bkyiv\b|\bzelensky\b",
    "Iran": r"\biran\b|\biranian\b|\btehran\b",
    "Israel": r"\bisrael\b|\bisraeli\b|\btel aviv\b",
    "NATO": r"\bnato\b",
    "European Union": r"\beuropean union\b|\beu\b",
}

TOPICS = {
    "Elections": r"\belection\w*\b|\bmidterm\b|\bprimary\b|\bballot\b|\bvoting\b|\bvoter\w*\b|\bpolling\b|\bredistrict\w*\b|\bcampaign\b",
    "Congress": r"\bcongress\b|\bsenate\b|\bhouse of representatives\b|\bbill\b|\blegislation\b|\bfilibuster\b|\bcommittee\b",
    "Executive": r"\bexecutive order\b|\bwhite house\b|\bpresident\b|\badministration\b|\bcabinet\b|\bagency\b",
    "Courts": r"\bsupreme court\b|\bfederal court\b|\bjudge\b|\blawsuit\b|\bruling\b|\bappeal\b|\binjunction\b",
    "Immigration": r"\bimmigration\b|\bdeport\w*\b|\bborder\b|\basylum\b|\bvisa\b|\bmigrant\w*\b",
    "Trade": r"\btariff\w*\b|\btrade\b|\bexport\w*\b|\bimport\w*\b|\bcustoms\b",
    "Foreign Policy": r"\bdiplomacy\b|\bdiplomatic\b|\bsummit\b|\btreaty\b|\balliance\b|\bsanction\w*\b|\bforeign policy\b|\benvoy\b",
    "Defense": r"\bdefense\b|\bmilitary\b|\bpentagon\b|\btroops\b|\bmissile\b|\bdrone\b|\bairstrike\b|\bnavy\b",
    "Economy": r"\binflation\b|\bjobs\b|\bemployment\b|\bgdp\b|\binterest rate\b|\bcentral bank\b|\beconomy\b|\bmarket\b|\bstocks\b|\bbond\b|\boil\b",
    "Public Opinion": r"\bpoll\w*\b|\bapproval\b|\bfavorability\b|\bsurvey\b|\bvoters\b|\bopinion\b",
}

STOP = set("the and that with from for this have has were will into about after before while says said their they them president latest report reports politics political news according amid over under its are was been being would could should where which what when how more than also very against between through during there here".split())


def clean_text(story):
    return re.sub(r"\s+", " ", f"{story.get('title','')} {story.get('summary','')}").strip().lower()


def tokens(story):
    words = re.findall(r"[a-z0-9]{4,}", clean_text(story))
    return {w for w in words if w not in STOP}


def entities(story):
    text = clean_text(story)
    return [name for name, pat in ENTITY_PATTERNS.items() if re.search(pat, text, re.I)]


def topics(story):
    text = clean_text(story)
    return [name for name, pat in TOPICS.items() if re.search(pat, text, re.I)]


def domain(story):
    url = str(story.get("source") or story.get("url") or "")
    host = urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    if host.endswith("gdeltproject.org"):
        label = str(story.get("sourceLabel") or "").lower()
        for known in ("cnn", "axios", "morsereport"):
            if known in label:
                return known
        return "gdelt-aggregate"
    return host or str(story.get("sourceLabel") or "unknown").lower()


def parse_time(story):
    value = story.get("time") or story.get("published") or story.get("updatedAt")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def similarity(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def event_match(a, b):
    ea, eb = set(entities(a)), set(entities(b))
    ta, tb = set(topics(a)), set(topics(b))
    shared_entities = len(ea & eb)
    shared_topics = len(ta & tb)
    sim = similarity(a, b)
    return ((shared_entities >= 2 and shared_topics >= 1 and sim >= 0.18) or
            (shared_entities >= 1 and shared_topics >= 1 and sim >= 0.32))


def main():
    data = json.loads(SNAP.read_text(encoding="utf-8"))
    stories = data.get("stories", [])
    political = [s for s in stories if s.get("intelligenceLayer") in ("us-politics", "world-politics")]

    for s in political:
        s["politicalEntities"] = entities(s)
        s["politicalTopics"] = topics(s)
        s["sourceDomain"] = domain(s)
        s["evidenceLevel"] = "SINGLE-SOURCE"
        s["corroboratingSources"] = []

    for i, story in enumerate(political):
        t = parse_time(story)
        matches = []
        for j, other in enumerate(political):
            if i == j or story["sourceDomain"] == other["sourceDomain"]:
                continue
            ot = parse_time(other)
            if t and ot and abs((t - ot).total_seconds()) > 24 * 3600:
                continue
            if event_match(story, other):
                matches.append(other)
        domains = sorted({m["sourceDomain"] for m in matches
                          if m.get("sourceDomain") not in ("", "unknown", "gdelt-aggregate")})
        if domains:
            story["evidenceLevel"] = "CORROBORATED"
            story["corroboratingSources"] = domains[:8]

    now = datetime.now(timezone.utc)
    for s in political:
        age = 48.0
        t = parse_time(s)
        if t:
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            age = max(0.0, (now - t).total_seconds() / 3600)
        recency = max(0, 48 - age) / 48 * 45
        corroboration = min(30, 15 * len(s.get("corroboratingSources", [])))
        breaking = 15 if s.get("breaking") else 0
        topic_bonus = min(10, 2 * len(s.get("politicalTopics", [])))
        s["politicalSignalScore"] = round(recency + corroboration + breaking + topic_bonus, 1)

    political.sort(key=lambda s: (s.get("politicalSignalScore", 0), s.get("time", "")), reverse=True)
    us = [s for s in political if s.get("intelligenceLayer") == "us-politics"]
    world = [s for s in political if s.get("intelligenceLayer") == "world-politics"]
    corroborated = [s for s in political if s.get("evidenceLevel") == "CORROBORATED"]
    source_counts = defaultdict(int)
    for s in political:
        source_counts[s.get("sourceDomain") or "unknown"] += 1

    data["politicalIntelligence"] = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "Deterministic event clustering using entity/topic overlap, time proximity, and independent source domains.",
        "caveat": "Corroboration means independent public reports describe a sufficiently similar event; it is not proof that every claim in those reports is true.",
        "totalSignals": len(political),
        "usPoliticsSignals": len(us),
        "worldPoliticsSignals": len(world),
        "corroboratedSignals": len(corroborated),
        "singleSourceSignals": len(political) - len(corroborated),
        "sourceCounts": dict(sorted(source_counts.items(), key=lambda x: (-x[1], x[0]))),
        "topSignals": political[:60],
    }
    data["usPolitics"] = us
    data["worldPolitics"] = world
    SNAP.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("POLITICAL INTELLIGENCE:", len(political), "signals;", len(corroborated), "corroborated")


if __name__ == "__main__":
    main()
