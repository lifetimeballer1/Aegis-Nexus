#!/usr/bin/env python3
"""Conservative claim/evidence layer for Global Pulse.

Important: report volume is not treated as independent confirmation. The
pipeline attempts to identify copied/syndicated reporting, separates source
domains from source families, records contradictions, and exposes the factors
behind each confidence label. It uses only public story metadata and never
collects visitor information.
"""
from __future__ import annotations
import hashlib, json, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SNAP = DATA / "snapshot.json"
OUT = DATA / "claims.json"
STOP = set("the a an and or of to in on for from with by as at is are was were be this that after before into near over under about against amid during report reports reported says said according officials official new latest global world breaking".split())
CATEGORY = {
    "conflict": re.compile(r"\b(war|fighting|battle|airstrike|air strike|shelling|invasion|armed clash|bombing|missile|drone strike|offensive|militant|insurgent|attack)\b", re.I),
    "politics": re.compile(r"\b(election|president|prime minister|government|parliament|coup|sanction|diplomatic|ceasefire|talks|treaty|minister)\b", re.I),
    "economics": re.compile(r"\b(inflation|tariff|trade|recession|gdp|interest rate|central bank|currency|debt|oil price|gas price|market|economy)\b", re.I),
    "disaster": re.compile(r"\b(earthquake|hurricane|cyclone|typhoon|flood|wildfire|landslide|volcano|tsunami)\b", re.I),
    "humanitarian": re.compile(r"\b(famine|hunger|refugee|displaced|humanitarian|cholera|outbreak|epidemic|food insecurity)\b", re.I),
}
CONTRADICTION = re.compile(r"\b(denies|denied|false|incorrect|disputed|no evidence|contradicts|not true|unconfirmed|refutes|refuted)\b", re.I)
NEGATION = re.compile(r"\b(no|not|never|denies|denied|false|without)\b", re.I)

# Common publisher aliases are intentionally conservative. Unknown domains are
# treated as their own family rather than guessed to be independent.
SOURCE_FAMILY = {
    "reuters.com": "reuters", "apnews.com": "ap", "afp.com": "afp",
    "bbc.com": "bbc", "bbc.co.uk": "bbc", "aljazeera.com": "aljazeera",
    "nytimes.com": "nytimes", "washingtonpost.com": "washpost",
    "theguardian.com": "guardian", "cnn.com": "cnn", "cnbc.com": "cnbc",
}

def clean_words(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    return [w for w in words if w not in STOP]

def domain(url: str) -> str:
    try:
        h = urlparse(url).netloc.lower().split(":")[0]
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""

def source_family(host: str) -> str:
    host = host.lower().removeprefix("www.")
    if host in SOURCE_FAMILY:
        return SOURCE_FAMILY[host]
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host

def normalized_title(text: str) -> str:
    words = clean_words(text)
    return " ".join(sorted(words[:24]))

def fingerprint(story: dict) -> str:
    title = normalized_title(str(story.get("title", "")))
    # A fingerprint is a candidate linkage, not proof of identity. We also
    # compare summaries below before collapsing reports into one evidence item.
    return hashlib.sha256(title.encode()).hexdigest()[:20]

def similarity(a: str, b: str) -> float:
    wa, wb = set(clean_words(a)), set(clean_words(b))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(1, len(wa | wb))

def category(text: str) -> str:
    for name, rx in CATEGORY.items():
        if rx.search(text):
            return name
    return "general"

def parse_time(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def is_copy(a: dict, b: dict) -> bool:
    at = str(a.get("title", "")) + " " + str(a.get("summary", ""))
    bt = str(b.get("title", "")) + " " + str(b.get("summary", ""))
    sim = similarity(at, bt)
    if sim >= 0.72:
        return True
    # Very similar headline + close publication time is a strong syndication
    # signal even when summaries differ.
    ts, us = parse_time(a.get("time", "")), parse_time(b.get("time", ""))
    if ts and us and abs((ts - us).total_seconds()) <= 3 * 3600 and similarity(str(a.get("title", "")), str(b.get("title", ""))) >= 0.65:
        return True
    return False

def independent_evidence(rows: list[dict]) -> list[dict]:
    selected = []
    for row in rows:
        host = domain(str(row.get("url", "")))
        fam = source_family(host) if host else "unknown"
        if not host:
            continue
        if any(r["family"] == fam and is_copy(row, r["row"]) for r in selected):
            continue
        selected.append({"row": row, "domain": host, "family": fam})
    return selected

def build(stories: list[dict]) -> dict:
    candidates = defaultdict(list)
    for s in stories:
        if isinstance(s, dict) and s.get("title") and s.get("url"):
            candidates[fingerprint(s)].append(s)

    claims = []
    for key, rows in candidates.items():
        rows.sort(key=lambda x: parse_time(x.get("time", "")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        evidence = independent_evidence(rows)
        domains = sorted({x["domain"] for x in evidence})
        families = sorted({x["family"] for x in evidence})
        text = " ".join(str(x.get("title", "")) for x in rows[:6])
        contradictory = [x for x in rows if CONTRADICTION.search(str(x.get("title", "")) + " " + str(x.get("summary", "")))]
        negated = [x for x in rows if NEGATION.search(str(x.get("title", "")))]
        independent_count = len(families)
        # Confidence is deliberately capped without independent evidence.
        if contradictory:
            confidence = "DISPUTED"
        elif independent_count >= 4:
            confidence = "HIGH"
        elif independent_count >= 2:
            confidence = "MODERATE"
        else:
            confidence = "LOW"
        latest = rows[0]
        claims.append({
            "id": "clm-" + key,
            "claim": str(latest.get("title", ""))[:240],
            "category": category(text),
            "confidence": confidence,
            "status": "disputed" if contradictory else ("corroborated" if independent_count >= 2 else "single-source"),
            "sourceCount": len(rows),
            "independentSourceDomains": len(domains),
            "independentSourceFamilies": independent_count,
            "sourceFamilies": families[:12],
            "copiedOrSyndicatedExcluded": max(0, len(rows) - len(evidence)),
            "contradictingReports": len(contradictory),
            "confidenceFactors": {
                "independentSourceFamilies": independent_count,
                "independentSourceDomains": len(domains),
                "contradictingReports": len(contradictory),
                "copiedOrSyndicatedExcluded": max(0, len(rows) - len(evidence)),
            },
            "sources": sorted({str(x.get("sourceLabel") or x.get("source") or "Unknown") for x in rows})[:12],
            "evidence": [{"source": x["row"].get("sourceLabel", "Unknown"), "domain": x["domain"], "family": x["family"], "url": x["row"].get("url", ""), "time": x["row"].get("time", ""), "title": str(x["row"].get("title", ""))[:240], "independent": True} for x in evidence[:12]],
            "lastObserved": latest.get("time", ""),
        })
    claims.sort(key=lambda c: (c["confidence"] == "HIGH", c["independentSourceFamilies"], c["independentSourceDomains"], c["sourceCount"]), reverse=True)
    return {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "Conservative candidate clustering with source-family independence, syndication/copy suppression, explicit contradictions, and explainable confidence factors.",
        "claims": claims[:200],
    }

def main():
    DATA.mkdir(exist_ok=True)
    snapshot = json.loads(SNAP.read_text(encoding="utf-8")) if SNAP.exists() else {}
    result = build(snapshot.get("stories") or [])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"CLAIMS: {len(result['claims'])} clusters")

if __name__ == "__main__":
    main()
