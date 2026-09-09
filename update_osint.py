#!/usr/bin/env python3
"""Sync public My Maps intelligence sources into Global Pulse.

All imported map reports remain explicitly unverified source-map evidence.
No browser API key is required; GitHub Actions fetches the public KML export.
"""
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SNAP = DATA / "snapshot.json"

MAP_SOURCES = [
    {
        "mid": "1LCWz0ynlXTMgdJYgKS89O_T5u_yh2QY",
        "name": "Global War News Map",
        "url": "https://www.google.com/maps/d/viewer?mid=1LCWz0ynlXTMgdJYgKS89O_T5u_yh2QY",
        "max_points": 250,
    },
    {
        "mid": "1fssgCzO1J6TnXS2SqlbutbaxbPQFo3I",
        "name": "Cartel Intelligence Map",
        "url": "https://www.google.com/maps/d/viewer?mid=1fssgCzO1J6TnXS2SqlbutbaxbPQFo3I",
        "max_points": 500,
    },
]

THEATERS = [
    ("mexico", "Mexico Cartel Conflict", "Latin America", ["mexico", "mexican", "cjng", "sinaloa", "cartel", "cartel violence", "narco"]),
    ("ecuador", "Ecuador Organized Crime Conflict", "Latin America", ["ecuador", "ecuadorian", "guayaquil", "los choneros", "prison violence"]),
    ("colombia", "Colombia Armed Groups", "Latin America", ["colombia", "colombian", "eln", "farc", "dissident", "catatumbo"]),
    ("haiti", "Haiti Gang Conflict", "Caribbean", ["haiti", "haitian", "port-au-prince", "gang violence"]),
    ("venezuela", "Venezuela Security / Political Risk", "Latin America", ["venezuela", "venezuelan", "caracas", "tren de aragua"]),
    ("guatemala", "Guatemala Organized Crime Risk", "Central America", ["guatemala", "guatemalan", "guatemala city"]),
    ("honduras", "Honduras Organized Crime Risk", "Central America", ["honduras", "honduran", "tegucigalpa", "san pedro sula"]),
    ("el-salvador", "El Salvador Security / Gang Risk", "Central America", ["el salvador", "salvadoran", "san salvador", "gang"]),
    ("belize", "Belize Security Risk", "Central America", ["belize", "belize city"]),
    ("costa-rica", "Costa Rica Organized Crime Risk", "Central America", ["costa rica", "costarican", "san jose costa rica"]),
    ("panama", "Panama Organized Crime / Trafficking Risk", "Central America", ["panama", "panamanian", "colon panama"]),
    ("brazil", "Brazil Organized Crime / Armed Groups", "South America", ["brazil", "brazilian", "rio de janeiro", "sao paulo", "pcc", "comando vermelho"]),
    ("peru", "Peru Organized Crime Risk", "South America", ["peru", "peruvian", "lima peru"]),
    ("bolivia", "Bolivia Organized Crime / Trafficking Risk", "South America", ["bolivia", "bolivian", "santa cruz bolivia"]),
    ("paraguay", "Paraguay Organized Crime / Trafficking Risk", "South America", ["paraguay", "paraguayan", "asuncion"]),
    ("argentina", "Argentina Organized Crime Risk", "South America", ["argentina", "argentine", "rosario argentina"]),
]


def fetch_kml(url):
    req = Request(url, headers={"User-Agent": "GlobalPulse/6.0"})
    raw = urlopen(req, timeout=35).read()
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not names:
                raise ValueError("KMZ contained no KML file")
            return zf.read(names[0])
    return raw


def clean_html(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.replace("&nbsp;", " ").strip()


def extract_urls(raw):
    urls = re.findall(r"https?://[^\s<>\"']+", raw or "", re.I)
    out = []
    for u in urls:
        u = u.rstrip(".,;:)]}")[:500]
        if u not in out:
            out.append(u)
    return out


def match_theater(blob):
    for cid, cname, region, aliases in THEATERS:
        if any(re.search(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])", blob) for a in aliases):
            return cid, cname, region
    return "", "", ""


def parse_points(kml_bytes, source, map_url, max_points):
    root = ET.fromstring(kml_bytes)
    seen = set()
    out = []
    for pm in root.findall(".//k:Placemark", {"k": "http://www.opengis.net/kml/2.2"}):
        name = (pm.findtext("k:name", default="", namespaces={"k": "http://www.opengis.net/kml/2.2"}) or "").strip()
        raw_description = pm.findtext("k:description", default="", namespaces={"k": "http://www.opengis.net/kml/2.2"}) or ""
        description = clean_html(raw_description)
        point = pm.find(".//k:Point/k:coordinates", {"k": "http://www.opengis.net/kml/2.2"})
        if point is None or not (point.text or "").strip():
            continue
        coords = (point.text or "").strip().split(",")
        if len(coords) < 2:
            continue
        try:
            lng, lat = float(coords[0]), float(coords[1])
        except ValueError:
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue

        key = (source, name.lower()[:120], round(lat, 4), round(lng, 4))
        if key in seen:
            continue
        seen.add(key)

        blob = f"{name} {description}".lower()
        cid, cname, region = match_theater(blob)
        urls = extract_urls(raw_description + " " + description)
        social_url = next((u for u in urls if re.search(r"(?:x\.com|twitter\.com)/", u, re.I)), "")
        url = social_url or (urls[0] if urls else "")

        importance = 3
        if any(k in blob for k in ("shooting", "shootout", "killed", "murder", "attack", "seized", "arrest", "massacre", "body", "bodies")):
            importance = 2
        if any(k in blob for k in ("major", "boss", "leader", "assault", "ambush", "military", "explosive", "mass killing")):
            importance = 1

        event_type = "organized-crime" if source == "Cartel Intelligence Map" else "conflict"
        out.append({
            "lat": round(lat, 5),
            "lng": round(lng, 5),
            "type": event_type,
            "layer": "osint",
            "importance": importance,
            "title": (name[:150] if name else f"{source} report"),
            "detail": description[:500] if description else f"Imported point from {source}",
            "url": url,
            "sourceUrl": url or map_url,
            "sourceMapUrl": map_url,
            "confidence": "SOURCE MAP REPORT / UNVERIFIED",
            "source": source,
            "conflictId": cid,
            "conflictName": cname,
            "region": region,
            "eventType": "Organized Crime" if source == "Cartel Intelligence Map" else "Conflict",
        })
        if len(out) >= max_points:
            break
    return out


def main():
    DATA.mkdir(exist_ok=True)
    snap = json.loads(SNAP.read_text()) if SNAP.exists() else {}
    sources = {s["name"]: s for s in MAP_SOURCES}

    managed_names = set(sources)
    base = [m for m in snap.get("markers", []) if m.get("source") not in managed_names]
    all_points = []
    statuses = []
    errors = []

    for cfg in MAP_SOURCES:
        name = cfg["name"]
        kml_url = f"https://www.google.com/maps/d/kml?forcekml=1&mid={cfg['mid']}"
        try:
            points = parse_points(fetch_kml(kml_url), name, cfg["url"], cfg["max_points"])
            all_points.extend(points)
            statuses.append(f"{name}: {len(points)} points")
        except Exception as exc:
            previous = [m for m in snap.get("markers", []) if m.get("source") == name]
            all_points.extend(previous)
            statuses.append(f"{name}: sync failed; kept {len(previous)} previous points")
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    snap["markers"] = base + all_points
    now = datetime.now(timezone.utc).isoformat()
    snap["updatedAt"] = now
    status = " | ".join(statuses)
    snap["sourceStatus"] = ((snap.get("sourceStatus", "") + "; ") if snap.get("sourceStatus") else "") + status

    # Canonical metadata consumed by the refresh pipeline. Version 4 means
    # both managed maps were processed by the current OSINT synchronizer.
    snap["osintMaps"] = {
        "version": 4,
        "updatedAt": now,
        "sources": [
            {
                "name": cfg["name"],
                "mapUrl": cfg["url"],
                "points": sum(1 for p in all_points if p.get("source") == cfg["name"]),
                "status": next((s for s in statuses if s.startswith(cfg["name"] + ":")), "unknown"),
            }
            for cfg in MAP_SOURCES
        ],
        "totalPoints": len(all_points),
        "errors": errors,
        "verification": "SOURCE MAP REPORT / UNVERIFIED",
    }

    note = snap.get("dataNote") or ""
    map_note = "Cartel Intelligence Map points are source-map reports and unverified until independently corroborated."
    if map_note not in note:
        snap["dataNote"] = (note + " " + map_note).strip()

    changes = snap.get("changes") or []
    changes.insert(0, {"kind": "osint", "title": "Intelligence map sync", "detail": status + (" — " + " | ".join(errors) if errors else "")})
    snap["changes"] = changes[:8]

    social = []
    for p in all_points:
        if p.get("url"):
            social.append({"label": p["title"][:100], "note": f"SOURCE MAP REPORT / UNVERIFIED — {p['source']}", "url": p["url"]})
        if len(social) >= 15:
            break
    if social:
        snap["social"] = social

    SNAP.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(status)


if __name__ == "__main__":
    main()
