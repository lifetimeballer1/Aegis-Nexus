"""Shared, deterministic intelligence scoring primitives.

Scores are evidence-derived and bounded to [0, 1]. This module deliberately
contains no network access or fabricated intelligence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import exp
from typing import Any, Mapping


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def recency_score(timestamp: Any, half_life_hours: float = 72.0, now: datetime | None = None) -> float:
    dt = parse_timestamp(timestamp)
    if dt is None:
        return 0.25
    now = now or datetime.now(timezone.utc)
    age_hours = max(0.0, (now - dt).total_seconds() / 3600.0)
    return clamp(exp(-0.69314718056 * age_hours / max(1.0, half_life_hours)))


def source_reliability(source: Mapping[str, Any] | None) -> float:
    source = source or {}
    explicit = source.get("reliability", source.get("source_reliability"))
    if explicit is not None:
        try:
            return clamp(float(explicit))
        except (TypeError, ValueError):
            pass
    tier = str(source.get("tier", "")).lower()
    return {"a": 0.95, "b": 0.85, "c": 0.70, "d": 0.55}.get(tier, 0.60)


def geopolitical_relevance(item: Mapping[str, Any] | None) -> float:
    item = item or {}
    explicit = item.get("geopolitical_relevance", item.get("geopoliticalRelevance"))
    if explicit is not None:
        try:
            return clamp(float(explicit))
        except (TypeError, ValueError):
            pass
    strategic = item.get("strategic_relevance", item.get("strategicRelevance"))
    if strategic is not None:
        try:
            return clamp(float(strategic))
        except (TypeError, ValueError):
            pass
    event_type = str(item.get("event_type", item.get("type", ""))).lower().replace(" ", "_")
    if event_type in _EVENT_SEVERITY:
        return _EVENT_SEVERITY[event_type]
    return 0.0


def evidence_score(evidence: Mapping[str, Any]) -> float:
    reliability = source_reliability(evidence)
    recency = recency_score(evidence.get("published_at", evidence.get("publishedAt", evidence.get("timestamp"))))
    quality = clamp(float(evidence.get("quality", evidence.get("evidence_quality", 0.75))))
    relevance = geopolitical_relevance(evidence)
    base = 0.45 * reliability + 0.40 * recency + 0.15 * quality
    return clamp(base * relevance)


_EVENT_SEVERITY = {
    "armed_conflict": 0.98, "military_strike": 0.95, "invasion": 1.0,
    "military_deployment": 0.88, "sanctions": 0.72, "diplomatic_crisis": 0.70,
    "election": 0.60, "trade": 0.55, "economic_policy": 0.52,
    "technology": 0.48, "energy": 0.55, "diplomacy": 0.45,
}


def event_severity(event: Mapping[str, Any]) -> float:
    explicit = event.get("severity")
    if explicit is not None:
        try:
            return clamp(float(explicit))
        except (TypeError, ValueError):
            pass
    event_type = str(event.get("event_type", event.get("type", ""))).lower().replace(" ", "_")
    return _EVENT_SEVERITY.get(event_type, 0.35)


def event_confidence(event: Mapping[str, Any], evidence: list[Mapping[str, Any]] | None = None) -> float:
    explicit = event.get("confidence")
    if explicit is not None:
        try:
            return clamp(float(explicit))
        except (TypeError, ValueError):
            pass
    scores = [evidence_score(e) for e in (evidence or [])]
    return clamp(sum(scores) / len(scores)) if scores else 0.30


def strategic_relevance(event: Mapping[str, Any]) -> float:
    explicit = event.get("strategic_relevance", event.get("strategicRelevance"))
    if explicit is not None:
        try:
            return clamp(float(explicit))
        except (TypeError, ValueError):
            pass
    return clamp(event_severity(event) * 0.70 + event_confidence(event) * 0.30)


def event_score(event: Mapping[str, Any], evidence: list[Mapping[str, Any]] | None = None) -> float:
    confidence = event_confidence(event, evidence)
    relevance = geopolitical_relevance(event)
    return clamp((0.35 * event_severity(event) + 0.25 * confidence + 0.20 * recency_score(event.get("timestamp", event.get("date", event.get("first_seen")))) + 0.20 * strategic_relevance(event)) * relevance)


def relationship_strength(relationship: Mapping[str, Any], evidence_scores: list[float] | None = None) -> float:
    explicit = relationship.get("strength")
    if explicit is not None:
        try:
            explicit_value = float(explicit)
            if explicit_value > 0:
                return clamp(explicit_value)
        except (TypeError, ValueError):
            pass
    evidence = clamp(sum(evidence_scores) / len(evidence_scores)) if evidence_scores else 0.30
    confidence = clamp(float(relationship.get("confidence", evidence)))
    occurrences = max(1, int(relationship.get("occurrences", relationship.get("count", 1))))
    recurrence = 1.0 - exp(-occurrences / 3.0)
    relevance = geopolitical_relevance(relationship)
    return clamp((0.55 * evidence + 0.30 * confidence + 0.15 * recurrence) * relevance)


def entity_importance(entity: Mapping[str, Any], event_scores: list[float] | None = None, evidence_scores: list[float] | None = None) -> float:
    """Score entities from evidence/events; zero is an initialization value, not an override."""
    explicit = entity.get("importance")
    if explicit is not None:
        try:
            explicit_value = float(explicit)
            if explicit_value > 0:
                return clamp(explicit_value)
        except (TypeError, ValueError):
            pass
    events = clamp(sum(event_scores) / len(event_scores)) if event_scores else 0.0
    evidence = clamp(sum(evidence_scores) / len(evidence_scores)) if evidence_scores else 0.0
    mentions = max(1, int(entity.get("mention_count", entity.get("mentions", 1))))
    recurrence = 1.0 - exp(-mentions / 5.0)
    return clamp(0.50 * events + 0.30 * evidence + 0.20 * recurrence)
