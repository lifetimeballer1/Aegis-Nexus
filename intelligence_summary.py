"""Build a compact, deterministic summary from canonical_intelligence.json.

Keeps dashboards and diagnostics from needing to parse the full canonical
artifact when they only need strategic entity and relationship metrics.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "data" / "canonical_intelligence.json"
OUTPUT = ROOT / "data" / "intelligence_summary.json"

FOCUS = {"United States", "China", "White House", "U.S. Congress", "U.S. Department of Defense", "U.S. Department of State", "U.S. Treasury", "Federal Reserve", "Communist Party of China", "People's Liberation Army", "Chinese State Council", "Chinese Ministry of Foreign Affairs", "Chinese Ministry of Commerce"}

def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    entities = data.get("entities", [])
    events = data.get("events", [])
    relationships = data.get("relationships", [])
    evidence = data.get("evidence", [])
    by_name = {str(e.get("canonical_name", e.get("name", ""))).casefold(): e for e in entities}
    strategic = []
    for e in entities:
        name = str(e.get("canonical_name", e.get("name", "")))
        if name in FOCUS:
            strategic.append({"id": e.get("id"), "name": name, "type": e.get("entity_type", e.get("type")), "importance": float(e.get("importance") or 0), "mentions": int(e.get("mentions") or e.get("mention_count") or 0)})
    strategic.sort(key=lambda x: (-x["importance"], -x["mentions"], x["name"]))
    def pick(name: str):
        e = by_name.get(name.casefold())
        if not e: return None
        return {"id": e.get("id"), "name": name, "importance": float(e.get("importance") or 0), "mentions": int(e.get("mentions") or e.get("mention_count") or 0)}
    type_counts = {}
    for r in relationships:
        kind = r.get("relationship_type", r.get("type", "unknown"))
        type_counts[kind] = type_counts.get(kind, 0) + 1
    summary = {"schema_version":"1.0","source":"canonical_intelligence.json","generated_at":data.get("generated_at"),"counts":{"entities":len(entities),"events":len(events),"relationships":len(relationships),"evidence":len(evidence)},"us":pick("United States"),"china":pick("China"),"strategic_actors":strategic,"relationship_types":dict(sorted(type_counts.items(), key=lambda x:(-x[1],x[0])))}
    OUTPUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

if __name__ == "__main__": main()
