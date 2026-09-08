#!/usr/bin/env python3
"""Trace U.S./China canonical event provenance before publication.

This is intentionally diagnostic: it does not mutate intelligence data. It resolves
country IDs and prints event actor/target/evidence chains so production failures can
be localized to extraction, target repair, or relationship promotion.
"""
from __future__ import annotations
import json
from pathlib import Path

DATA = Path("data")
CANONICAL = DATA / "canonical_intelligence.json"
COUNTRIES = ("United States", "China")


def main() -> int:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    entities = {str(e.get("id")): e for e in data.get("entities", []) if isinstance(e, dict)}
    ids_by_name = {str(e.get("canonical_name")): str(e.get("id")) for e in entities.values()}
    evidence = {str(e.get("id")): e for e in data.get("evidence", []) if isinstance(e, dict)}
    relationships = [r for r in data.get("relationships", []) if isinstance(r, dict)]
    print("=== STRATEGIC PROVENANCE TRACE ===")
    for country in COUNTRIES:
        cid = ids_by_name.get(country)
        events = [e for e in data.get("events", []) if cid and cid in {str(x) for x in e.get("actor_ids", [])}]
        targeted = [event for event in events if event.get('target_ids')]
        print(f"{country}: entity_id={cid} actor_events={len(events)} targeted={len(targeted)}")
        # Always expose every targeted event, even when it falls beyond the
        # first twenty articles. These are the production acceptance evidence.
        for event in targeted + [event for event in events if not event.get('target_ids')][:20]:
            actors = [entities.get(str(x), {}).get("canonical_name", str(x)) for x in event.get("actor_ids", [])]
            targets = [entities.get(str(x), {}).get("canonical_name", str(x)) for x in event.get("target_ids", [])]
            evs = [evidence.get(str(x), {}) for x in event.get("evidence_ids", [])]
            urls = [str(e.get("url") or "") for e in evs if e]
            print(f"  event={event.get('id')} type={event.get('event_type')} actors={actors} targets={targets} evidence={len(evs)} urls={urls[:2]}")
            for item in evs:
                print(f"    title={item.get('title')} excerpt={item.get('excerpt')}")
            for rel in relationships:
                if str(event.get("id")) in {str(x) for x in rel.get("event_ids", [])}:
                    print(f"    relationship={rel.get('relationship_type')} source={entities.get(str(rel.get('source_entity_id')),{}).get('canonical_name')} target={entities.get(str(rel.get('target_entity_id')),{}).get('canonical_name')} evidence_ids={rel.get('evidence_ids')}")
    print("=== END TRACE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
