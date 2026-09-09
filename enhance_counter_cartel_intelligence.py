#!/usr/bin/env python3
"""Add curated, evidence-backed Operation Southern Spear relationships and map theater nodes.

This layer complements the co-occurrence graph. It only adds relationships that are
explicitly documented by public U.S. government/SOUTHCOM reporting. Map points are
regional/theater reference nodes unless the source gives an exact incident location.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / "data" / "snapshot.json"

SOUTHCOM = "https://www.southcom.mil/Commanders-Imperatives/Countering-Narcoterrorism-and-Cartels/"
OSS_UPDATE = "https://www.southcom.mil/MEDIA/NEWS-ARTICLES/Article/4589266/officials-provide-progress-update-on-major-operation-1-year-after-its-launch/"
OSS_Q2 = "https://media.defense.gov/2026/May/21/2003935694/-1/-1/1/OSS_Q2_MAR2026_FINAL_508.pdf"
SEPT2 = "https://www.southcom.mil/News/PressReleases/Article/4589814/interdiction-of-narco-terrorist-refueling-vessel-sept-2-2026/"
SEPT3 = "https://www.southcom.mil/News/PressReleases/Article/4591068/interdiction-of-narco-terrorist-refueling-vessel-sept-3-2026/"
AUG28 = "https://www.southcom.mil/News/PressReleases/Article/4586154/interdiction-of-narco-terrorist-refueling-vessel-aug-28-2026/"
AUG25 = "https://www.southcom.mil/News/PressReleases/Article/4583027/lethal-kinetic-strike-august-25-2026/"
AUG23 = "https://www.southcom.mil/News/PressReleases/Article/4580933/lethal-kinetic-strike-august-23-2026/"
COLOMBIA = "https://www.southcom.mil/News/PressReleases/Article/4585871/gen-donovan-visits-colombia/"
AUG4 = "https://www.southcom.mil/News/PressReleases/Article/4564574/southcom-establishes-joint-task-force-western-hemisphere/"

EVIDENCE = {
    "oss": {"title": "Operation Southern Spear — SOUTHCOM counter-narcoterrorism campaign", "url": SOUTHCOM, "source": "U.S. Southern Command"},
    "oss_update": {"title": "Officials provide progress update on Operation Southern Spear", "url": OSS_UPDATE, "source": "U.S. Southern Command"},
    "oss_q2": {"title": "Operation Southern Spear — Report to Congress, Jan. 1–Mar. 31, 2026", "url": OSS_Q2, "source": "U.S. Department of Defense / Lead IG"},
    "sept2": {"title": "Interdiction of Narco-Terrorist Refueling Vessel, Sept. 2, 2026", "url": SEPT2, "source": "U.S. Southern Command"},
    "sept3": {"title": "Interdiction of Narco-Terrorist Refueling Vessel, Sept. 3, 2026", "url": SEPT3, "source": "U.S. Southern Command"},
    "aug28": {"title": "Interdiction of Narco-Terrorist Refueling Vessel, Aug. 28, 2026", "url": AUG28, "source": "U.S. Southern Command"},
    "aug25": {"title": "Lethal Kinetic Strike, Aug. 25, 2026", "url": AUG25, "source": "U.S. Southern Command"},
    "aug23": {"title": "Lethal Kinetic Strike, Aug. 23, 2026", "url": AUG23, "source": "U.S. Southern Command"},
    "colombia": {"title": "Gen. Donovan visits Colombia and Ecuador border region", "url": COLOMBIA, "source": "U.S. Southern Command"},
    "jtf": {"title": "SOUTHCOM establishes Joint Task Force Western Hemisphere", "url": AUG4, "source": "U.S. Southern Command"},
}

def ev(key, detail):
    x = dict(EVIDENCE[key]); x["summary"] = detail; x["time"] = "2026-09-05T00:00:00Z"; return x

def node(graph, label, kind, evidence=None):
    sid = label.lower().replace(" & ", " and ").replace("/", "-").replace(" ", "-")
    sid = "".join(c for c in sid if c.isalnum() or c == "-")
    existing = next((n for n in graph["nodes"] if str(n.get("label") or n.get("name")) == label), None)
    if existing:
        if evidence and not any(e.get("title") == evidence.get("title") for e in existing.get("evidence", [])):
            existing.setdefault("evidence", []).append(evidence)
        return existing["id"]
    graph["nodes"].append({"id": sid, "label": label, "kind": kind, "mentions": 1, "evidence": [evidence] if evidence else []})
    return sid

def edge(graph, source, target, relationship, evidence):
    for e in graph["edges"]:
        if {e.get("source"), e.get("target")} == {source, target}:
            e["weight"] = max(1, int(e.get("weight") or 1)) + 1
            e.setdefault("types", [])
            if "curated" not in e["types"]: e["types"].append("curated")
            e["relationship"] = relationship
            if not any(x.get("title") == evidence.get("title") for x in e.get("evidence", [])):
                e.setdefault("evidence", []).append(evidence)
            e["evidenceCount"] = len(e["evidence"])
            return
    graph["edges"].append({"source": source, "target": target, "weight": 1, "types": ["curated"], "relationship": relationship, "evidence": [evidence], "evidenceCount": 1})

def marker(markers, lat, lng, title, region, detail, source_url, event_type):
    key = title.lower()
    if any(str(m.get("title", "")).lower() == key for m in markers): return
    markers.append({"lat": lat, "lng": lng, "type": "strategic", "layer": "counter-cartel", "importance": 3, "title": title, "detail": detail, "url": source_url, "sourceUrl": source_url, "source": "Operation Southern Spear / SOUTHCOM", "region": region, "eventType": event_type, "confidence": "DOCUMENTED THEATER / NOT AN EXACT INCIDENT COORDINATE"})

def main():
    data = json.loads(SNAP.read_text(encoding="utf-8"))
    graph = data.get("intelligenceGraph") if isinstance(data.get("intelligenceGraph"), dict) else {}
    graph.setdefault("nodes", []); graph.setdefault("edges", [])
    # Campaign structure: U.S. -> SOUTHCOM -> JTF-WHEM / Operation Southern Spear -> regional partners and named organizations.
    us = node(graph, "United States", "actor", ev("oss", "SOUTHCOM describes Operation Southern Spear as a U.S. counter-narcoterrorism campaign intended to defend the U.S. homeland."))
    southcom = node(graph, "U.S. Southern Command", "organization", ev("oss", "SOUTHCOM states it uses Operation Southern Spear, joint task forces, intelligence fusion and partner operations to detect, disrupt and dismantle cartel networks."))
    oss = node(graph, "Operation Southern Spear", "operation", ev("oss_update", "SOUTHCOM describes Southern Spear as a large-scale U.S. military and counter-narcoterrorism campaign in the Western Hemisphere."))
    jtf = node(graph, "Joint Task Force Western Hemisphere", "military", ev("jtf", "SOUTHCOM established JTF-WHEM to accelerate and synchronize operations against destabilizing narco-terrorist networks."))
    a3c = node(graph, "Americas Counter Cartel Coalition", "coalition", ev("colombia", "SOUTHCOM documents A3C coordination with Ecuador and Colombia to dismantle cartel networks and leadership."))
    coast_guard = node(graph, "U.S. Coast Guard", "military", ev("oss", "SOUTHCOM describes maritime interdiction operations with the U.S. Coast Guard as part of its counter-cartel effort."))
    ecuador = node(graph, "Ecuador", "actor", ev("sept3", "SOUTHCOM reports U.S.-Ecuador coordination in Eastern Pacific interdictions and joint counter-narcoterrorism activity."))
    colombia = node(graph, "Colombia", "actor", ev("colombia", "SOUTHCOM documents joint U.S.-Colombia security work and an A3C meeting in the Colombia-Ecuador border region."))
    mexico = node(graph, "Mexico", "actor", ev("oss_q2", "The Southern Spear congressional report identifies multiple Mexico-based trafficking organizations and describes their U.S. presence/routes."))
    los_choneros = node(graph, "Los Choneros", "organized-crime", ev("sept3", "SOUTHCOM says intelligence confirmed an interdicted Eastern Pacific refueling vessel was supporting Los Choneros."))
    sinaloa = node(graph, "Sinaloa Cartel", "organized-crime", ev("oss_q2", "The Southern Spear congressional report identifies the Cártel de Sinaloa and documents its presence in Mexico and the United States."))
    cjng = node(graph, "CJNG", "organized-crime", ev("oss_q2", "The Southern Spear congressional report identifies Cártel de Jalisco Nueva Generación and documents its Mexican and international/U.S. presence."))
    clan = node(graph, "Clan del Golfo", "organized-crime", ev("oss_q2", "The Southern Spear congressional report identifies Clan del Golfo in Colombia and describes cocaine trafficking routes toward Central America, Mexico and the United States."))
    venezuela = node(graph, "Venezuela", "actor", ev("oss_q2", "The Southern Spear congressional report identifies Venezuela-based trafficking organizations and their U.S.-linked trafficking activity."))
    caribbean = node(graph, "Caribbean Maritime Theater", "strategic", ev("aug25", "SOUTHCOM reported a lethal strike on Aug. 25 against a go-fast vessel on established narco-trafficking routes in the Caribbean."))
    eastern_pacific = node(graph, "Eastern Pacific Maritime Theater", "strategic", ev("sept3", "SOUTHCOM reported Aug. 23 and Sept. 2–3 operations against vessels operating on Eastern Pacific narco-trafficking routes."))
    us_homeland = node(graph, "U.S. Homeland", "strategic", ev("oss_update", "SOUTHCOM describes the campaign as defending the U.S. homeland and disrupting drugs before they reach American communities."))

    edge(graph, us, southcom, "U.S. Southern Command is the U.S. geographic combatant command directing the documented campaign activity.", EVIDENCE["oss"])
    edge(graph, southcom, oss, "SOUTHCOM identifies Operation Southern Spear as a core counter-narcoterrorism operation in its area of responsibility.", EVIDENCE["oss_update"])
    edge(graph, oss, jtf, "JTF-WHEM is a force structure established to execute/synchronize the campaign's Western Hemisphere counter-cartel mission.", EVIDENCE["jtf"])
    edge(graph, oss, coast_guard, "Southern Spear includes maritime interdiction activity with the U.S. Coast Guard and interagency partners.", EVIDENCE["oss"])
    edge(graph, oss, caribbean, "Documented Southern Spear activity includes maritime interdictions and lethal operations in the Caribbean.", EVIDENCE["aug25"])
    edge(graph, oss, eastern_pacific, "Documented Southern Spear/JTF-WHEM activity includes lethal and interdiction operations on Eastern Pacific trafficking routes.", EVIDENCE["sept3"])
    edge(graph, oss, us_homeland, "SOUTHCOM explicitly frames the campaign around defending the U.S. homeland and preventing drugs from reaching U.S. communities.", EVIDENCE["oss_update"])
    edge(graph, jtf, ecuador, "JTF-WHEM has conducted documented interdictions in coordination with Ecuador.", EVIDENCE["sept3"])
    edge(graph, jtf, los_choneros, "SOUTHCOM says JTF-WHEM interdicted a refueling vessel supporting Los Choneros.", EVIDENCE["sept3"])
    edge(graph, jtf, caribbean, "JTF-WHEM conducted a documented lethal strike against a vessel on Caribbean trafficking routes.", EVIDENCE["aug25"])
    edge(graph, jtf, eastern_pacific, "JTF-WHEM conducted documented lethal/interdiction operations on Eastern Pacific trafficking routes.", EVIDENCE["sept2"])
    edge(graph, a3c, ecuador, "SOUTHCOM documents A3C coordination with Ecuador against transnational criminal networks.", EVIDENCE["colombia"])
    edge(graph, a3c, colombia, "SOUTHCOM documents A3C coordination with Colombia and Ecuador in the border region.", EVIDENCE["colombia"])
    edge(graph, southcom, colombia, "SOUTHCOM documents a security partnership with Colombia focused on countering narco-terrorists.", EVIDENCE["colombia"])
    edge(graph, southcom, ecuador, "SOUTHCOM documents support and coordination with Ecuador against transnational criminal organizations.", EVIDENCE["sept3"])
    edge(graph, oss, sinaloa, "The Southern Spear congressional report identifies Sinaloa as a sanctioned drug-trafficking organization with extensive U.S. presence/routes.", EVIDENCE["oss_q2"])
    edge(graph, oss, cjng, "The Southern Spear congressional report identifies CJNG as a sanctioned drug-trafficking organization with operations extending into the United States.", EVIDENCE["oss_q2"])
    edge(graph, oss, clan, "The Southern Spear congressional report identifies Clan del Golfo and describes cocaine routes toward Mexico and the United States.", EVIDENCE["oss_q2"])
    edge(graph, oss, mexico, "The Southern Spear congressional report identifies multiple Mexico-based trafficking organizations and their U.S.-linked routes/presence.", EVIDENCE["oss_q2"])
    edge(graph, oss, venezuela, "Southern Spear reporting includes Venezuela-linked maritime interdiction activity and Venezuela-based trafficking organizations.", EVIDENCE["oss_q2"])
    edge(graph, mexico, sinaloa, "The congressional Southern Spear report identifies Sinaloa as based in Mexico.", EVIDENCE["oss_q2"])
    edge(graph, mexico, cjng, "The congressional Southern Spear report identifies CJNG as based in Mexico.", EVIDENCE["oss_q2"])
    edge(graph, colombia, clan, "The congressional Southern Spear report identifies Clan del Golfo as Colombia-based.", EVIDENCE["oss_q2"])
    edge(graph, ecuador, los_choneros, "SOUTHCOM reports Los Choneros-linked maritime activity operating from/with Ecuadorian cooperation context.", EVIDENCE["sept3"])
    edge(graph, us, sinaloa, "The Southern Spear congressional report documents Sinaloa's presence in the United States and the U.S. campaign's counter-narcoterrorism mission.", EVIDENCE["oss_q2"])
    edge(graph, us, cjng, "The Southern Spear congressional report documents CJNG's growing U.S. presence and the campaign's counter-narcoterrorism mission.", EVIDENCE["oss_q2"])
    edge(graph, us, clan, "The Southern Spear congressional report documents Clan del Golfo trafficking routes reaching the United States.", EVIDENCE["oss_q2"])

    markers = data.get("markers") if isinstance(data.get("markers"), list) else []
    marker(markers, 18.22, -66.59, "Operation Southern Spear — Puerto Rico / Caribbean staging region", "Puerto Rico / Caribbean", "Regional reference node: SOUTHCOM documents Southern Spear maritime activity and Marine/Sailor forces operating in the Caribbean theater. Not an exact incident coordinate.", OSS_UPDATE, "COUNTER-CARTEL THEATER")
    marker(markers, 14.0, -70.0, "Operation Southern Spear — Caribbean maritime theater", "Caribbean Sea", "Regional reference node for documented Southern Spear maritime interdiction and lethal-strike activity. Not an exact incident coordinate.", AUG25, "COUNTER-CARTEL THEATER")
    marker(markers, 0.0, -92.0, "Operation Southern Spear — Eastern Pacific maritime theater", "Eastern Pacific", "Regional reference node for documented Aug. 23 and Sept. 2–3 operations on narco-trafficking routes. Not an exact incident coordinate.", SEPT3, "COUNTER-CARTEL THEATER")
    marker(markers, -0.95, -80.7, "Ecuador — Los Choneros / U.S. counter-cartel link", "Ecuador", "SOUTHCOM reports U.S.-Ecuador coordination and an Eastern Pacific interdiction of a refueling vessel supporting Los Choneros.", SEPT3, "COUNTER-CARTEL NODE")
    marker(markers, 1.4, -78.9, "Colombia-Ecuador border — A3C corridor", "Colombia / Ecuador", "SOUTHCOM documents a trilateral A3C meeting and joint strategy in a cocaine-trafficking corridor.", COLOMBIA, "COUNTER-CARTEL NODE")
    marker(markers, 19.43, -99.13, "Mexico — major cartel network node", "Mexico", "Reference node for Southern Spear reporting on Mexico-based organizations including Sinaloa and CJNG and their U.S. reach. Not an incident coordinate.", OSS_Q2, "CARTEL NETWORK NODE")
    marker(markers, 6.24, -75.58, "Colombia — Clan del Golfo / trafficking network node", "Colombia", "Reference node for Southern Spear reporting on Colombia-based Clan del Golfo and cocaine routes toward Central America, Mexico and the United States.", OSS_Q2, "CARTEL NETWORK NODE")
    marker(markers, 10.48, -66.90, "Venezuela — trafficking / maritime pressure node", "Venezuela", "Reference node for Southern Spear reporting on Venezuela-based trafficking organizations and Caribbean maritime activity. Not an incident coordinate.", OSS_Q2, "COUNTER-CARTEL NODE")
    marker(markers, 39.0, -98.5, "United States — homeland exposure / destination", "United States", "Reference node: Southern Spear reporting frames the campaign around protecting the U.S. homeland and disrupting trafficking routes reaching American communities. Not an incident coordinate.", OSS_UPDATE, "HOMELAND EXPOSURE")

    graph["updatedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    graph["method"] = "Evidence-backed public reporting graph plus curated government-documented Southern Spear relationships"
    graph["caution"] = "Curated connections are limited to relationships explicitly described by public government/SOUTHCOM reporting. A connection does not by itself prove causation, coordination, alliance, or responsibility. Map theater nodes are regional references unless an exact incident location is documented."
    data["intelligenceGraph"] = graph
    data["markers"] = markers
    data["counterCartelLayer"] = {"campaign": "Operation Southern Spear", "updatedAt": graph["updatedAt"], "coverage": ["SOUTHCOM", "JTF-WHEM", "A3C", "U.S. Coast Guard", "Caribbean", "Eastern Pacific", "Ecuador", "Colombia", "Mexico", "Venezuela", "U.S. homeland"], "note": "Evidence-backed campaign layer; map theater nodes are not exact strike coordinates unless explicitly stated."}
    data["changes"] = ([{"kind":"intelligence","title":"Southern Spear relationship layer expanded","detail":"Added documented U.S.-SOUTHCOM-JTF-WHEM-A3C-cartel relationships and regional counter-cartel map nodes."}] + (data.get("changes") or []))[:10]
    SNAP.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Southern Spear layer: {len(graph['nodes'])} nodes / {len(graph['edges'])} edges / {len(markers)} map markers")

if __name__ == "__main__":
    main()
