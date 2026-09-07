#!/usr/bin/env python3
"""Promote explicit event actor/target pairs into typed relationships.

This never invents a relationship: both endpoints must already be present in an
existing event's actor_ids/target_ids and the relationship keeps the event's
source evidence and action context.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "data" / "canonical_intelligence.json"
TYPE_MAP = {
    "sanction": "sanctions",
    "military_action": "military_action_against",
    "diplomatic_action": "negotiates_with",
    "trade_action": "trades_with",
    "economic_action": "economic_action_toward",
    "technology_action": "technology_action_toward",
    "energy_action": "energy_action_toward",
    "cyber_activity": "cyber_action_against",
    "political_action": "political_action_toward",
}

COUNTRY_INSTITUTIONS = {
    "United States": {
        "U.S. Department of Defense", "U.S. Department of State", "U.S. Treasury",
        "U.S. Department of Commerce", "U.S. Department of Justice", "U.S. Congress",
        "White House",
    },
    "China": {
        "People's Liberation Army", "Communist Party of China", "Chinese State Council",
        "Chinese Central Military Commission", "Chinese Ministry of Foreign Affairs",
        "Chinese Ministry of Commerce",
    },
}

def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    entities = {str(e.get("id")): e for e in data.get("entities", [])}
    relationships = data.setdefault("relationships", [])
    index = {(str(r.get("source_entity_id")), str(r.get("relationship_type")), str(r.get("target_entity_id"))): r for r in relationships}

    # Country attribution bridge: country-specific institutions are already
    # required to be action-local actors by the canonical builder. When one is
    # an event actor, add the corresponding sovereign country to actor_ids.
    # This preserves provenance instead of relying on article-wide co-mentions.
    entity_ids_by_name = {str(e.get("canonical_name")): str(e.get("id")) for e in data.get("entities", [])}
    country_actor_bridges = 0
    for event in data.get("events", []):
        actors = [str(x) for x in event.get("actor_ids", []) if str(x) in entities]
        actor_names = {str(entities[x].get("canonical_name")) for x in actors}
        for country, institutions in COUNTRY_INSTITUTIONS.items():
            country_id = entity_ids_by_name.get(country)
            if not country_id:
                continue
            if actor_names & institutions and country_id not in actors:
                event["actor_ids"] = list(event.get("actor_ids", [])) + [country_id]
                actors.append(country_id)
                country_actor_bridges += 1

    promoted = 0
    for event in data.get("events", []):
        actors = [str(x) for x in event.get("actor_ids", []) if str(x) in entities]
        targets = [str(x) for x in event.get("target_ids", []) if str(x) in entities]
        kind = TYPE_MAP.get(str(event.get("event_type")))
        if not kind or not actors or not targets:
            continue
        for actor in actors:
            for target in targets:
                if actor == target:
                    continue
                key = (actor, kind, target)
                rel = index.get(key)
                if rel is None:
                    rel = {
                        "source_entity_id": actor,
                        "relationship_type": kind,
                        "target_entity_id": target,
                        "confidence": float(event.get("confidence") or 0.65),
                        "weight": 0.0,
                        "first_seen": event.get("timestamp", ""),
                        "last_seen": event.get("timestamp", ""),
                        "evidence_ids": [],
                        "event_ids": [],
                        "geopolitical_relevance": float(event.get("geopolitical_relevance") or event.get("strategic_relevance") or 0),
                    }
                    relationships.append(rel)
                    index[key] = rel
                    promoted += 1
                rel["confidence"] = max(float(rel.get("confidence") or 0), float(event.get("confidence") or 0))
                rel["geopolitical_relevance"] = max(float(rel.get("geopolitical_relevance") or 0), float(event.get("geopolitical_relevance") or event.get("strategic_relevance") or 0))
                ts = event.get("timestamp", "")
                if ts:
                    if not rel.get("first_seen") or ts < rel["first_seen"]: rel["first_seen"] = ts
                    if ts > rel.get("last_seen", ""): rel["last_seen"] = ts
                for eid in event.get("evidence_ids", []):
                    if eid not in rel["evidence_ids"]: rel["evidence_ids"].append(eid)
                if event.get("id") not in rel["event_ids"]: rel["event_ids"].append(event["id"])
                rel["weight"] = max(float(rel.get("weight") or 0), float(event.get("score") or 0))

    # Any remaining typed relationship must have a resolvable event/evidence trail.
    # Unsupported legacy typed edges are discarded rather than presented as facts.
    valid_event_ids = {str(e.get("id")) for e in data.get("events", [])}
    valid_evidence_ids = {str(e.get("id")) for e in data.get("evidence", [])}
    cleaned=[]
    removed_unproven=0
    for rel in relationships:
        if rel.get("relationship_type") == "mentioned_with":
            cleaned.append(rel)
            continue
        event_ids=[str(x) for x in rel.get("event_ids", []) if str(x) in valid_event_ids]
        evidence_ids=[str(x) for x in rel.get("evidence_ids", []) if str(x) in valid_evidence_ids]
        if not event_ids or not evidence_ids:
            removed_unproven += 1
            continue
        rel["event_ids"]=event_ids
        rel["evidence_ids"]=evidence_ids
        cleaned.append(rel)
    relationships=cleaned
    semantic_pairs={(str(r.get("source_entity_id")),str(r.get("target_entity_id"))) for r in relationships if r.get("relationship_type")!="mentioned_with"}
    before=len(relationships)
    relationships=[r for r in relationships if not (r.get("relationship_type")=="mentioned_with" and (str(r.get("source_entity_id")),str(r.get("target_entity_id"))) in semantic_pairs)]
    data["relationships"]=relationships
    data.setdefault("metadata",{})["semantic_relationship_enrichment"]="actor-target-event-v3"
    data["metadata"]["strategic_country_actor_bridge"]="institution-backed-v1"
    data["metadata"]["semantic_relationship_count"]=sum(r.get("relationship_type")!="mentioned_with" for r in relationships)
    data["metadata"]["cooccurrence_relationship_count"]=sum(r.get("relationship_type")=="mentioned_with" for r in relationships)
    PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"PASS: semantic enrichment country_actor_bridges={country_actor_bridges} promoted={promoted} relationships={len(relationships)} removed_cooccurrence={before-len(relationships)} removed_unproven={removed_unproven}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
