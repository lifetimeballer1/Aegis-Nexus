#!/usr/bin/env python3
"""Build the public Global Pulse snapshot from no-key RSS sources."""
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SNAP = DATA / "snapshot.json"
HIST = DATA / "history.json"
SOURCES = DATA / "sources.json"

FEEDS = [
    ("SOUTHCOM Official Reporting — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Asouthcom.mil&mode=ArtList&format=rss&maxrecords=100&timespan=24h", "southcom"),
    ("Google News — SOUTHCOM", "https://news.google.com/rss/search?q=SOUTHCOM+US+Southern+Command+military+when%3A1d&hl=en-US&gl=US&ceid=US:en", "southcom-news"),
    ("Google News — Operation Southern Spear", "https://news.google.com/rss/search?q=%22Operation+Southern+Spear%22+cartel+narco-terrorism+when%3A1d&hl=en-US&gl=US&ceid=US:en", "counter-cartel"),
    ("Google News — Joint Task Force Western Hemisphere", "https://news.google.com/rss/search?q=%22Joint+Task+Force+Western+Hemisphere%22+cartel+when%3A1d&hl=en-US&gl=US&ceid=US:en", "counter-cartel"),
    ("Google News — Americas Counter Cartel Coalition", "https://news.google.com/rss/search?q=%22Americas+Counter+Cartel+Coalition%22+when%3A1d&hl=en-US&gl=US&ceid=US:en", "counter-cartel"),
    ("Google News — U.S. Counter-Cartel Operations", "https://news.google.com/rss/search?q=US+military+cartels+narco-terrorism+Ecuador+Mexico+Caribbean+Eastern+Pacific+when%3A1d&hl=en-US&gl=US&ceid=US:en", "counter-cartel"),
    ("Google News — Los Choneros", "https://news.google.com/rss/search?q=%22Los+Choneros%22+Ecuador+US+military+when%3A1d&hl=en-US&gl=US&ceid=US:en", "cartel"),
    ("Google News — Sinaloa Cartel / CJNG", "https://news.google.com/rss/search?q=Sinaloa+Cartel+CJNG+US+military+Mexico+when%3A1d&hl=en-US&gl=US&ceid=US:en", "cartel"),
    ("GDELT — Western Hemisphere Counter-Cartel", "https://api.gdeltproject.org/api/v2/doc/doc?query=(SOUTHCOM%20OR%20%22Southern%20Spear%22%20OR%20%22Joint%20Task%20Force%20Western%20Hemisphere%22%20OR%20cartel%20OR%20narco-terrorism%20OR%20Los%20Choneros%20OR%20CJNG%20OR%20Sinaloa)&mode=ArtList&format=rss&maxrecords=250&timespan=15m", "counter-cartel"),

    ("GDACS Global Disaster Alerts", "https://www.gdacs.org/xml/rss.xml", "climate-hazard"),
    ("GDELT Climate & Disaster Watch", "https://api.gdeltproject.org/api/v2/doc/doc?query=(drought%20OR%20flood%20OR%20wildfire%20OR%20cyclone%20OR%20hurricane%20OR%20heatwave%20OR%20famine%20OR%20food%20insecurity%20OR%20epidemic%20OR%20outbreak)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "climate-hazard"),
    ("GDELT Climate Security Watch", "https://api.gdeltproject.org/api/v2/doc/doc?query=(drought%20OR%20flood%20OR%20famine%20OR%20water%20shortage%20OR%20food%20crisis%20OR%20disease%20OR%20epidemic)%20AND%20(country%20OR%20government%20OR%20security%20OR%20migration)&mode=ArtList&format=rss&maxrecords=150&timespan=1h", "climate-hazard"),
    ("FAO GIEWS", "https://www.fao.org/giews/english/ew/ewr.xml", "food-security"),
    ("NPR Politics", "https://feeds.npr.org/1014/rss.xml", "us-politics"),
    ("Fox News Politics", "https://moxie.foxnews.com/google-publisher/politics.xml", "us-politics"),
    ("CNN Politics — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Acnn.com%20AND%20(politics%20OR%20Trump%20OR%20Congress%20OR%20Senate%20OR%20election%20OR%20White%20House)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "us-politics"),
    ("Axios Politics — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Aaxios.com%20AND%20(politics%20OR%20Trump%20OR%20Congress%20OR%20Senate%20OR%20election%20OR%20White%20House%20OR%20midterms)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "us-politics"),
    ("Morse Report — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Amorsereport.com%20AND%20(politics%20OR%20Trump%20OR%20Congress%20OR%20Senate%20OR%20election%20OR%20White%20House)&mode=ArtList&format=rss&maxrecords=100&timespan=24h", "us-politics"),

    ("GDELT Live — U.S. Politics", "https://api.gdeltproject.org/api/v2/doc/doc?query=(Trump%20OR%20Congress%20OR%20Senate%20OR%20House%20OR%20Supreme%20Court%20OR%20election%20OR%20midterms%20OR%20White%20House)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "us-politics"),
    ("GDELT Live — World Politics", "https://api.gdeltproject.org/api/v2/doc/doc?query=(election%20OR%20president%20OR%20parliament%20OR%20prime%20minister%20OR%20diplomacy%20OR%20summit%20OR%20sanctions%20OR%20alliance)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "world-politics"),
    ("GDELT Live — Global Economics", "https://api.gdeltproject.org/api/v2/doc/doc?query=(oil%20OR%20inflation%20OR%20tariff%20OR%20trade%20OR%20interest%20rate%20OR%20central%20bank%20OR%20stocks%20OR%20bonds%20OR%20currency)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "economics"),
    ("NPR Politics", "https://feeds.npr.org/1014/rss.xml", "us-politics"),
    ("Fox News Politics", "https://moxie.foxnews.com/google-publisher/politics.xml", "us-politics"),
    ("CNN Politics — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Acnn.com%20AND%20(politics%20OR%20Trump%20OR%20Congress%20OR%20Senate%20OR%20election%20OR%20White%20House)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "us-politics"),
    ("Axios Politics — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Aaxios.com%20AND%20(politics%20OR%20Trump%20OR%20Congress%20OR%20Senate%20OR%20election%20OR%20White%20House%20OR%20midterms)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "us-politics"),
    ("Morse Report — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Amorsereport.com%20AND%20(politics%20OR%20Trump%20OR%20Congress%20OR%20Senate%20OR%20election%20OR%20White%20House)&mode=ArtList&format=rss&maxrecords=100&timespan=24h", "us-politics"),

    ("GDELT Live — U.S. Politics", "https://api.gdeltproject.org/api/v2/doc/doc?query=(Trump%20OR%20Congress%20OR%20Senate%20OR%20House%20OR%20Supreme%20Court%20OR%20election%20OR%20midterms%20OR%20White%20House)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "us-politics"),
    ("GDELT Live — World Politics", "https://api.gdeltproject.org/api/v2/doc/doc?query=(election%20OR%20president%20OR%20parliament%20OR%20prime%20minister%20OR%20diplomacy%20OR%20summit%20OR%20sanctions%20OR%20alliance)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "world-politics"),
    ("GDELT Live — Global Economics", "https://api.gdeltproject.org/api/v2/doc/doc?query=(oil%20OR%20inflation%20OR%20tariff%20OR%20trade%20OR%20interest%20rate%20OR%20central%20bank%20OR%20stocks%20OR%20bonds%20OR%20currency)&mode=ArtList&format=rss&maxrecords=200&timespan=15m", "economics"),
    ("NPR Politics", "https://feeds.npr.org/1014/rss.xml", "us-politics"),

    ("GDELT Live — Global", "https://api.gdeltproject.org/api/v2/doc/doc?query=(war%20OR%20conflict%20OR%20military%20OR%20sanctions%20OR%20election%20OR%20crisis)&mode=ArtList&format=rss&maxrecords=250&timespan=15m", "live"),
    ("GDELT Live — Africa", "https://api.gdeltproject.org/api/v2/doc/doc?query=(africa%20OR%20sudan%20OR%20congo%20OR%20sahel%20OR%20nigeria%20OR%20somalia)&mode=ArtList&format=rss&maxrecords=150&timespan=15m", "africa"),
    ("GDELT Live — Americas", "https://api.gdeltproject.org/api/v2/doc/doc?query=(mexico%20OR%20colombia%20OR%20venezuela%20OR%20brazil%20OR%20haiti%20OR%20ecuador%20OR%20peru)&mode=ArtList&format=rss&maxrecords=150&timespan=15m", "americas"),
    ("GDELT Live — Middle East", "https://api.gdeltproject.org/api/v2/doc/doc?query=(gaza%20OR%20iran%20OR%20israel%20OR%20yemen%20OR%20syria%20OR%20iraq)&mode=ArtList&format=rss&maxrecords=150&timespan=15m", "middle-east"),

    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "international"),
    ("BBC Middle East", "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "regional"),
    ("BBC Africa", "https://feeds.bbci.co.uk/news/world/africa/rss.xml", "regional"),
    ("BBC Asia", "https://feeds.bbci.co.uk/news/world/asia/rss.xml", "regional"),
    ("BBC Europe", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", "regional"),
    ("BBC Americas", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", "regional"),
    ("Guardian World", "https://www.theguardian.com/world/rss", "international"),
    ("Guardian US", "https://www.theguardian.com/us-news/rss", "regional"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml", "international"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "international"),
    ("DW World", "https://rss.dw.com/rdf/rss-en-world", "international"),
    ("France 24", "https://www.france24.com/en/rss", "international"),
    ("Crisis Group", "https://www.crisisgroup.org/rss.xml", "analysis"),
    ("ReliefWeb", "https://reliefweb.int/updates/rss.xml", "humanitarian"),
]

CONFLICTS = [    ("western-hemisphere-cartel", "Western Hemisphere Counter-Cartel Campaign", "Western Hemisphere", "CRIMINAL CONFLICT", "HIGH", ["socom", "southcom", "southern command", "operation southern spear", "southern spear", "joint task force western hemisphere", "jtf-whem", "americas counter cartel coalition", "counter cartel", "narco-terrorism", "narco terrorist", "narco-terrorist", "cartel", "los choneros", "sinaloa cartel", "cjng"]),

    ("ukraine", "Ukraine–Russia War", "Europe", "WAR", "HIGH", ["ukraine", "russia", "kyiv", "donetsk", "crimea", "kharkiv", "zaporizhzhia", "zelensky", "putin"]),
    ("gaza", "Gaza / Israel–Hamas", "Middle East", "WAR", "HIGH", ["gaza", "hamas", "gaza strip", "rafah", "west bank", "palestinian", "israel-hamas"]),
    ("israel-iran", "Israel–Iran Regional Front", "Middle East", "WAR", "HIGH", ["israel-iran", "israel iran", "iran israel", "tehran", "iranian nuclear", "iranian missile"]),
    ("hormuz", "Iran / Strait of Hormuz", "Middle East", "FLASHPOINT", "HIGH", ["strait of hormuz", "hormuz", "persian gulf", "gulf tanker", "iran oil shipping"]),
    ("yemen", "Yemen / Red Sea", "Middle East", "CONFLICT", "HIGH", ["yemen", "houthi", "red sea", "bab el-mandeb", "aden shipping"]),
    ("syria", "Syria Conflict / Residual Fronts", "Middle East", "CONFLICT", "MODERATE", ["syria", "syrian", "damascus", "idlib"]),
    ("iraq", "Iraq Militia / Security Risk", "Middle East", "CONFLICT", "MODERATE", ["iraq", "iraqi", "baghdad", "kurdistan iraq", "iraqi militia"]),
    ("sudan", "Sudan Civil War", "Africa", "WAR", "CRITICAL", ["sudan", "sudanese", "khartoum", "darfur", "kordofan", "rsf", "saf sudan"]),
    ("south-sudan", "South Sudan Instability", "Africa", "CONFLICT", "HIGH", ["south sudan", "juba", "south sudanese"]),
    ("drc", "Eastern DRC Conflict", "Africa", "CONFLICT", "HIGH", ["democratic republic of congo", "drc", "eastern congo", "goma", "m23", "north kivu", "south kivu"]),
    ("somalia", "Somalia / al-Shabaab", "Africa", "INSURGENCY", "HIGH", ["somalia", "somali", "al-shabaab", "mogadishu"]),
    ("ethiopia", "Ethiopia Internal Conflict Risk", "Africa", "CONFLICT", "MODERATE", ["ethiopia", "ethiopian", "amhara", "tigray", "oromia"]),
    ("nigeria", "Nigeria Insurgency / Banditry", "Africa", "INSURGENCY", "HIGH", ["nigeria", "nigerian", "boko haram", "iswap", "banditry", "bandits"]),
    ("sahel-mali", "Mali / Sahel Insurgency", "Africa", "INSURGENCY", "HIGH", ["mali", "malian", "jnim", "bamako"]),
    ("sahel-burkina", "Burkina Faso Insurgency", "Africa", "INSURGENCY", "HIGH", ["burkina faso", "burkinabe", "jnim", "ouagadougou"]),
    ("sahel-niger", "Niger Insurgency / Coup Fallout", "Africa", "INSURGENCY", "HIGH", ["niger", "nigerien", "niamey", "jnim", "islamic state sahel"]),
    ("cameroon", "Cameroon Separatist Conflict", "Africa", "INSURGENCY", "MODERATE", ["cameroon", "cameroonian", "anglophone", "ambazonia"]),
    ("chad", "Chad Security / Sahel Spillover", "Africa", "FLASHPOINT", "MODERATE", ["chad", "chadian", "n'djamena", "lake chad"]),
    ("libya", "Libya Political / Militia Risk", "Africa", "CONFLICT", "MODERATE", ["libya", "libyan", "tripoli libya", "benghazi libya"]),
    ("mozambique", "Mozambique Cabo Delgado", "Africa", "INSURGENCY", "MODERATE", ["mozambique", "mozambican", "cabo delgado", "mocimboa"]),
    ("myanmar", "Myanmar Civil War", "Asia", "WAR", "HIGH", ["myanmar", "burma", "myanmarese", "junta", "rakhine", "mandalay", "naypyidaw"]),
    ("afghanistan", "Afghanistan Security Risk", "Asia", "INSURGENCY", "MODERATE", ["afghanistan", "afghan", "taliban", "isis-k", "kabul"]),
    ("pakistan", "Pakistan Militancy / Border Risk", "Asia", "INSURGENCY", "HIGH", ["pakistan", "pakistani", "ttp", "balochistan", "islamabad"]),
    ("taiwan", "Taiwan Strait Pressure", "Indo-Pacific", "FLASHPOINT", "HIGH", ["taiwan", "taiwan strait", "pla", "beijing", "cross-strait"]),
    ("korea", "Korean Peninsula", "Indo-Pacific", "FLASHPOINT", "HIGH", ["north korea", "south korea", "dprk", "pyongyang", "korean peninsula"]),
    ("south-china-sea", "South China Sea Flashpoint", "Indo-Pacific", "FLASHPOINT", "MODERATE", ["south china sea", "philippines china", "spratly", "second thomas shoal"]),
    ("haiti", "Haiti Gang Conflict", "Caribbean", "CRIMINAL CONFLICT", "CRITICAL", ["haiti", "haitian", "port-au-prince", "gang violence haiti"]),
    ("mexico", "Mexico Cartel Conflict", "Latin America", "CRIMINAL CONFLICT", "HIGH", ["mexico", "mexican", "cjng", "sinaloa cartel", "cartel violence", "mexico cartel"]),
    ("ecuador", "Ecuador Organized Crime Conflict", "Latin America", "CRIMINAL CONFLICT", "HIGH", ["ecuador", "ecuadorian", "guayaquil", "los choneros", "prison violence ecuador"]),
    ("colombia", "Colombia Armed Groups", "Latin America", "INSURGENCY", "MODERATE", ["colombia", "colombian", "eln", "farc dissidents", "catatumbo"]),
]

BREAKING_RE = re.compile(r"strike|attack|killed|drone|missile|blockade|escalat|invasion|ceasefire|bomb|shell|offensive|mobiliz|sanction|hostage|explosion|raid|coup|clash|shooting|airstrike", re.I)
CONFLICT_RE = re.compile(r"war|conflict|military|troops|forces|attack|strike|missile|drone|airstrike|shelling|insurgent|militant|clash|ceasefire|coup|cartel|gang|kidnap|bomb|explosion", re.I)
ECON_RE = re.compile(r"oil|gas|inflation|tariff|trade|market|stocks|bond|currency|dollar|euro|yuan|yen|interest rate|central bank|economy|sanction|shipping|freight|commodity", re.I)
DIPLO_RE = re.compile(r"talks|summit|negotiat|diplomat|ceasefire|peace|agreement|treaty|alliance|sanction|tariff|embassy|envoy", re.I)
MIL_RE = re.compile(r"missile|drone|troops|military|army|navy|air force|fighter|carrier|exercise|mobiliz|weapons|defense", re.I)
SEVERITY = [("critical", re.compile(r"invasion|mass casualty|massacre|major offensive|missile barrage|bombing campaign|blockade|airstrike|explosion|coup", re.I), 12), ("high", re.compile(r"strike|attack|killed|drone|missile|shelling|clash|raid|hostage|shooting", re.I), 8), ("medium", re.compile(r"troops|military|sanction|ceasefire|mobiliz|threat|warning", re.I), 4)]


def fetch(url):
    req = Request(url, headers={"User-Agent": "GlobalPulse/7.0 (+https://github.com/lifetimeballer1/global-pulse)"})
    with urlopen(req, timeout=25) as response:
        return response.read()


def clean(value):
    return re.sub(r"<[^>]+>", " ", value or "").replace("&nbsp;", " ").strip()


def text(node, tag):
    found = node.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def is_breaking(title, summary):
    return bool(BREAKING_RE.search(f"{title} {summary}"))


def parse_time(value):
    if not value: return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try: return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception: return None


def recency_weight(value):
    dt = parse_time(value)
    if not dt: return 0.65
    age = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
    if age <= 6: return 1.0
    if age <= 24: return 0.92
    if age <= 72: return 0.75
    if age <= 168: return 0.55
    return 0.35


def alias_present(alias, text_value):
    return re.search(r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])", text_value.lower()) is not None


def match_conflict(story, aliases):
    title, summary = story["title"], story["summary"]
    score, matched = 0.0, []
    for alias in aliases:
        if alias_present(alias, title):
            score += 6.0; matched.append(alias)
        elif alias_present(alias, summary):
            score += 2.5; matched.append(alias)
    if not matched: return 0.0, []
    blob = f"{title} {summary}"
    severity_bonus = max((points for _, rx, points in SEVERITY if rx.search(blob)), default=0)
    return min(32.0, score + severity_bonus * recency_weight(story["time"])), matched


def baseline_score(level):
    return {"CRITICAL": 46, "HIGH": 37, "MODERATE": 27}.get(level, 22)


def make_conflicts(stories, previous):
    result, previous_by_id = [], {c.get("id"): c for c in previous.get("conflicts", [])}
    for cid, name, region, category, baseline, aliases in CONFLICTS:
        ranked = []
        for story in stories:
            score, matched = match_conflict(story, aliases)
            if score > 0: ranked.append((score, story, matched))
        ranked.sort(key=lambda x: (x[0], parse_time(x[1]["time"]) or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        source_names = {story["sourceLabel"] for _, story, _ in ranked}
        recent = ranked[0][1] if ranked else None
        evidence = sum(min(32.0, score) for score, _, _ in ranked[:8])
        breadth_bonus = min(18, max(0, len(source_names) - 1) * 5)
        activity = round(min(100, baseline_score(baseline) + evidence * 0.72 + breadth_bonus))
        old_activity = previous_by_id.get(cid, {}).get("activityScore")
        delta = activity - old_activity if isinstance(old_activity, (int, float)) else 0
        escalation = "CRITICAL" if activity >= 82 else "HIGH" if activity >= 68 else "MODERATE" if activity >= 50 else "LOW"
        if len(source_names) >= 3: confidence = "CORROBORATED"
        elif len(source_names) == 2: confidence = "MULTI-SOURCE"
        elif len(source_names) == 1: confidence = "SINGLE-SOURCE"
        else: confidence = "MONITORING"
        event_type = "MONITORING"
        if recent:
            blob = f"{recent['title']} {recent['summary']}"
            if re.search(r"missile|drone|airstrike|bomb|explosion|shell", blob, re.I): event_type = "KINETIC"
            elif re.search(r"troops|military|exercise|mobiliz|weapons", blob, re.I): event_type = "MILITARY POSTURE"
            elif re.search(r"ceasefire|talks|negotiat|peace|agreement|diplomat", blob, re.I): event_type = "DIPLOMATIC"
            elif re.search(r"oil|gas|shipping|sanction|trade|tariff", blob, re.I): event_type = "ECONOMIC"
            elif re.search(r"gang|cartel|kidnap|crime", blob, re.I): event_type = "CRIMINAL VIOLENCE"
        signals = [{"title": story["title"][:180], "source": story["sourceLabel"], "url": story["source"], "time": story["time"], "match": matched[:4], "signal": round(score, 1)} for score, story, matched in ranked[:4]]
        result.append({
            "id": cid, "name": name, "region": region, "category": category,
            "status": "Active signal" if ranked else "Monitoring",
            "recent": recent["title"][:180] if recent else "No specific current signal in the public feed window.",
            "escalation": escalation, "activityScore": activity, "delta": delta,
            "signalCount": len(ranked), "sourceCount": len(source_names),
            "confidence": confidence, "eventType": event_type,
            "lastSignal": recent["time"] if recent else None, "signals": signals,
            "facts": f"{len(ranked)} conflict-specific signal(s) from {len(source_names)} source(s) in the current feed window.",
            "analysis": "Score combines theater-specific identifiers, event severity, source breadth, and recency. It measures reporting activity, not battlefield truth, casualties, or probability of war."
        })
    return sorted(result, key=lambda c: c["activityScore"], reverse=True)


def score_dimension(stories, regex, base=40):
    weighted = sum(recency_weight(s["time"]) for s in stories if regex.search(f"{s['title']} {s['summary']}"))
    return round(max(0, min(100, base + weighted * 3.2)))


def main():
    DATA.mkdir(exist_ok=True)
    old = load_json(SNAP, {})
    stories, errors = [], []
    for label, url, kind in FEEDS:
        try:
            root = ET.fromstring(fetch(url))
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:18]:
                title = clean(text(item, "title") or text(item, "{http://www.w3.org/2005/Atom}title"))
                link = text(item, "link")
                if not link:
                    node = item.find("{http://www.w3.org/2005/Atom}link")
                    link = node.attrib.get("href", "") if node is not None else ""
                summary = clean(text(item, "description") or text(item, "{http://www.w3.org/2005/Atom}summary"))
                pub = text(item, "pubDate") or text(item, "{http://www.w3.org/2005/Atom}updated")
                if not title or not link: continue
                stories.append({"id": hashlib.sha1(link.encode()).hexdigest()[:12], "sourceLabel": label, "sourceType": kind, "title": title[:240], "summary": summary[:420], "source": link, "time": pub, "tag": "Breaking" if is_breaking(title, summary) else "World", "confidence": "DEVELOPING", "breaking": is_breaking(title, summary)})
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}")
    unique, seen = [], set()
    for story in stories:
        if story["id"] not in seen:
            seen.add(story["id"]); unique.append(story)
    unique.sort(key=lambda s: parse_time(s["time"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    stories = unique[:300]
    old_ids = {s.get("id") for s in old.get("stories", [])}
    new_items = [s for s in stories if s["id"] not in old_ids]
    breakdown = {"Conflict activity": score_dimension(stories, CONFLICT_RE, 35), "Diplomatic strain": score_dimension(stories, DIPLO_RE, 32), "Economic pressure": score_dimension(stories, ECON_RE, 32), "Market volatility": score_dimension(stories, re.compile(r"market|stocks|bond|currency|oil|gas|volatil", re.I), 30), "Military posture": score_dimension(stories, MIL_RE, 34)}
    tension = round(sum(breakdown.values()) / len(breakdown))
    old_tension = old.get("tension")
    delta = tension - old_tension if isinstance(old_tension, (int, float)) else 0
    changes = [{"kind": "breaking" if s["breaking"] else "new reporting", "title": s["title"][:150], "detail": f"{s['sourceLabel']} · {s['sourceType']} · {s['confidence']}"} for s in new_items[:10]]
    if not changes: changes = [{"kind": "refresh", "title": "Public sources checked — no new unique headlines", "detail": f"{len(FEEDS)} feeds checked; {len(stories)} current stories retained."}]
    conflicts = make_conflicts(stories, old)
    now = datetime.now(timezone.utc).isoformat()
    snapshot = {"updatedAt": now, "sourceStatus": f"{len(stories)} stories · {len(new_items)} new · {len(FEEDS)-len(errors)}/{len(FEEDS)} feeds healthy", "dataNote": "Public RSS aggregation. Conflict scores are theater-specific analytical signals based on current reporting, source breadth, event severity, and recency. They are not official conflict measurements.", "tension": tension, "tensionDelta": delta, "breakdownScores": breakdown, "changes": changes, "conflicts": conflicts, "markers": old.get("markers", []), "social": old.get("social", []), "stories": stories, "sourceHealth": [{"name": label, "type": kind, "status": "error" if any(e.startswith(label + ":") for e in errors) else "ok"} for label, _, kind in FEEDS]}
    SNAP.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    history = load_json(HIST, [])
    history.append({"updatedAt": now, "tension": tension, "delta": delta})
    HIST.write_text(json.dumps(history[-240:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    SOURCES.write_text(json.dumps({"updatedAt": now, "feeds": [{"name": a, "url": b, "type": c, "domain": urlparse(b).netloc} for a, b, c in FEEDS], "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(snapshot["sourceStatus"], "tension", tension, "conflicts", len(conflicts))
    if errors: print("errors:", "; ".join(errors))


def load_json(path, default):
    try: return json.loads(path.read_text()) if path.exists() else default
    except Exception: return default


if __name__ == "__main__":
    main()
