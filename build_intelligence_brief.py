#!/usr/bin/env python3
"""Build a compact, explainable intelligence brief from existing Global Pulse artifacts.

No LLM or API key is required. The brief is a deterministic prioritization layer:
- live events provide current developments;
- assessments provide risk/attention indicators;
- snapshot metadata provides freshness and source-health context.

This deliberately avoids inventing facts or causal explanations. It surfaces the
strongest available signals and points the UI back to the underlying event data.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def load(name, default):
    path = DATA / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def iso_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def event_score(event):
    confidence = str(event.get("confidence", "low")).lower()
    confidence_score = {"high": 4, "moderate": 3, "medium": 3, "limited": 2, "low": 1, "unverified": 0}.get(confidence, 0)
    reports = int(event.get("reportCount") or len(event.get("reports") or []))
    independent = int(event.get("sourceCount") or len({
        (r.get("credit") or {}).get("sourceId") or r.get("sourceLabel")
        for r in (event.get("reports") or [])
        if (r.get("credit") or {}).get("sourceId") or r.get("sourceLabel")
    }))
    breaking = 4 if any(r.get("breaking") for r in (event.get("reports") or [])) else 0
    return breaking + confidence_score * 3 + min(reports, 8) + min(independent, 6)


def event_record(event):
    reports = event.get("reports") or []
    sources = []
    seen = set()
    for report in reports:
        source = (report.get("credit") or {}).get("sourceId") or report.get("sourceLabel")
        if source and source not in seen:
            seen.add(source)
            sources.append(source)
    return {
        "id": event.get("id"),
        "title": event.get("title", "Untitled event"),
        "category": event.get("category", "general"),
        "confidence": event.get("confidence", "low"),
        "reportCount": int(event.get("reportCount") or len(reports)),
        "independentSourceCount": len(sources),
        "sources": sources[:12],
        "breaking": any(r.get("breaking") for r in reports),
        "firstSeen": event.get("firstSeen") or None,
        "lastSeen": event.get("lastSeen") or None
    }


def assessment_record(item):
    return {
        "entity": item.get("entity"),
        "score": item.get("score"),
        "level": item.get("level"),
        "delta": item.get("delta", 0),
        "evidenceCount": item.get("evidenceCount", 0),
        "topFactors": [f for f in (item.get("factors") or []) if f.get("delta") is not None][:4]
    }


def main():
    events_doc = load("live_events.json", {})
    assessment_doc = load("intelligence_assessment.json", {})
    snapshot = load("snapshot.json", {})

    events = sorted(events_doc.get("events") or [], key=event_score, reverse=True)
    assessments = sorted(
        assessment_doc.get("assessments") or [],
        key=lambda x: (int(x.get("score") or 0), int(x.get("evidenceCount") or 0)),
        reverse=True,
    )

    brief = {
        "version": 1,
        "updatedAt": iso_now(),
        "method": "Deterministic prioritization of existing public Global Pulse artifacts; not a forecast or causal model.",
        "freshness": {
            "snapshotUpdatedAt": snapshot.get("updatedAt"),
            "eventsUpdatedAt": events_doc.get("updatedAt"),
            "assessmentsUpdatedAt": assessment_doc.get("updatedAt")
        },
        "headline": {
            "title": "Global Intelligence Brief",
            "description": "Highest-priority developments and attention indicators from the latest generated intelligence artifacts."
        },
        "topDevelopments": [event_record(e) for e in events[:10]],
        "watchlist": [assessment_record(a) for a in assessments[:10]],
        "methodology": {
            "developmentPriority": "Breaking signal + evidence volume + independent-source count + reported confidence.",
            "watchlistPriority": "Assessment score followed by available evidence count.",
            "caution": "Priority is not truth probability. Repeated syndicated reports may not be independent confirmation."
        }
    }
    (DATA / "intelligence_brief.json").write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Built intelligence brief: {len(brief['topDevelopments'])} developments / {len(brief['watchlist'])} watchlist entities")


if __name__ == "__main__":
    main()
