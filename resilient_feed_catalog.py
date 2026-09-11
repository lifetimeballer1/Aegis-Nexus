#!/usr/bin/env python3
"""Canonical no-key feed catalog for Global Pulse.

Favors direct publisher RSS plus Google News RSS search feeds so coverage can
expand without API keys. Topic feeds are intentionally specific so smaller
conflicts are not drowned out by major-war headlines.
"""
from urllib.parse import quote_plus

def google(query: str) -> str:
    q = quote_plus(f"{query} when:1d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

FEEDS = [
    ("GDACS Global Disaster Alerts", "https://www.gdacs.org/xml/rss.xml", "climate-hazard"),
    ("NPR News", "https://feeds.npr.org/1001/rss.xml", "us-politics"),
    ("Fox News Politics", "https://moxie.foxnews.com/google-publisher/politics.xml", "us-politics"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "international"),
    ("BBC Middle East", "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "regional"),
    ("BBC Africa", "https://feeds.bbci.co.uk/news/world/africa/rss.xml", "regional"),
    ("BBC Asia", "https://feeds.bbci.co.uk/news/world/asia/rss.xml", "regional"),
    ("BBC Europe", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", "regional"),
    ("Guardian World", "https://www.theguardian.com/world/rss", "international"),
    ("Guardian US", "https://www.theguardian.com/us-news/rss", "regional"),
    ("NPR National Security", "https://feeds.npr.org/1122/rss.xml", "international"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "international"),
    ("DW World", "https://rss.dw.com/xml/rss-en-world", "international"),
    ("RFI World", "https://www.rfi.fr/en/general/rss", "international"),
    # France 24 https://www.france24.com/en/rss quarantined 2026-09-09: endpoint now
    # serves an HTML page instead of RSS (verified live). RFI is its France Medias
    # Monde sister outlet and covers the same French-world brief.
    ("Crisis Group", "https://www.crisisgroup.org/rss.xml", "analysis"),
    # Western Hemisphere / SOUTHCOM counter-cartel intelligence feeds.
    ("SOUTHCOM Official Reporting — GDELT Mirror", "https://api.gdeltproject.org/api/v2/doc/doc?query=domain%3Asouthcom.mil&mode=ArtList&format=rss&maxrecords=100&timespan=24h", "southcom"),
    ("Google News — SOUTHCOM", google("SOUTHCOM US Southern Command military Caribbean Eastern Pacific"), "southcom-news"),
    ("Google News — Operation Southern Spear", google('"Operation Southern Spear"'), "counter-cartel"),
    ("Google News — Joint Task Force Western Hemisphere", google('"Joint Task Force Western Hemisphere" cartel'), "counter-cartel"),
    ("Google News — Americas Counter Cartel Coalition", google('"Americas Counter Cartel Coalition"'), "counter-cartel"),
    ("Google News — U.S. Counter-Cartel Operations", google("US military cartels narco-terrorism Ecuador Mexico Caribbean Eastern Pacific"), "counter-cartel"),
    ("Google News — Los Choneros", google('"Los Choneros" Ecuador US military'), "cartel"),
    ("Google News — Sinaloa Cartel / CJNG", google("Sinaloa Cartel CJNG Mexico"), "cartel"),
    ("GDELT — Western Hemisphere Counter-Cartel", "https://api.gdeltproject.org/api/v2/doc/doc?query=(SOUTHCOM%20OR%20%22Southern%20Spear%22%20OR%20%22Joint%20Task%20Force%20Western%20Hemisphere%22%20OR%20cartel%20OR%20narco-terrorism%20OR%20%22Los%20Choneros%22%20OR%20CJNG%20OR%20Sinaloa)&mode=ArtList&format=rss&maxrecords=100&timespan=6h", "counter-cartel"),
    # Freshness sweep 2026-09-11 (12 cheap web_fetch validators, 6 new LIVE):
    # - USGS M4.5+ day atom updated 2026-09-11T17:36:50Z (M4.7 Colombia entry same day)
    # - BBC Latin America lastBuildDate Fri 11 Sep 2026 17:36 GMT (minutes fresh)
    # - RFI Africa lastBuildDate Fri 11 Sep 2026 16:07 GMT (DRC Bukavu story)
    # - InSight Crime hourly, lastBuildDate Thu 10 Sep 2026 (cartel analysis)
    # - UN News lastBuildDate Fri 11 Sep 2026 (humanitarian/global)
    # - DoD News Releases (war.gov redirect) lastBuildDate Fri 11 Sep 2026 17:32 GMT
    # Rejected (verified dead/blocked, NOT added): CNN topstories serves stale
    # 2024 cache; ReliefWeb 406 bot-block; AP 403 Cloudflare; SOUTHCOM direct
    # RSS empty octet-stream; RFI /americas redirects to /international (dup).
    ("USGS M4.5+ Earthquakes — Past Day", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.atom", "climate-hazard"),
    ("BBC Latin America", "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml", "regional"),
    ("RFI Africa", "https://www.rfi.fr/en/africa/rss", "regional"),
    ("InSight Crime", "https://insightcrime.org/feed/", "analysis"),
    ("UN News — Global", "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "humanitarian"),
    ("DoD News Releases", "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=9&Site=945", "security"),
    ("Google News — Climate & Disaster", google("flood wildfire hurricane disaster"), "climate-hazard"),
    ("Google News — Climate Security", google("climate crisis food water"), "climate-hazard"),
    ("Google News — Humanitarian", google("humanitarian crisis disaster displacement food insecurity emergency"), "humanitarian"),
    ("Google News — U.S. Politics", google("US politics Congress Senate White House election"), "us-politics"),
    ("Google News — CNN Politics", google("site:cnn.com politics Trump Congress Senate White House"), "us-politics"),
    ("Google News — Axios Politics", google("site:axios.com politics Trump Congress Senate White House"), "us-politics"),
    ("Google News — Morse Report", google("Morse Report politics"), "us-politics"),
    ("Google News — World Politics", google("election parliament diplomacy"), "world-politics"),
    ("Google News — Global Economics", google("oil inflation tariff trade interest rate central bank stocks bonds currency"), "economics"),
    ("Google News — Global Conflict", google("war conflict military sanctions crisis attack airstrike missile drone"), "live"),
    ("Google News — Africa Security", google("Africa conflict Sudan Sahel"), "africa"),
    ("Google News — Sudan Conflict", google("Sudan SAF RSF Darfur conflict"), "africa-conflict"),
    ("Google News — DRC / M23", google("DRC Congo M23 Goma Bukavu armed conflict Rwanda"), "africa-conflict"),
    ("Google News — Sahel Security", google("Mali Burkina Faso Niger Sahel jihadist insurgency military"), "africa-conflict"),
    ("Google News — Somalia Security", google("Somalia al Shabaab"), "africa-conflict"),
    ("Google News — Haiti Security", google("Haiti gangs Port-au-Prince transitional government security"), "americas-conflict"),
    ("Google News — Mexico Cartel Conflict", google("Mexico cartel Sinaloa"), "americas-conflict"),
    ("Google News — Ecuador Security", google("Ecuador organized crime gangs military security conflict"), "americas-conflict"),
    ("Google News — Myanmar Civil War", google("Myanmar junta resistance conflict"), "asia-conflict"),
    ("Google News — Afghanistan Security", google("Afghanistan Taliban"), "south-asia-conflict"),
    ("Google News — Yemen / Red Sea", google("Yemen Houthis Red Sea shipping missile drone conflict"), "middle-east-conflict"),
    ("Google News — Iran Israel", google("Iran Israel conflict missile drone strike escalation"), "middle-east-conflict"),
    ("Google News — Ukraine War", google("Ukraine Russia war frontline missile drone strike"), "europe-conflict"),
    ("Google News — South America Security", google("South America Colombia Venezuela Brazil Ecuador Peru conflict crime military"), "americas"),
    ("Google News — Middle East Security", google("Gaza Iran Israel Yemen Syria Iraq conflict missile drone"), "middle-east"),
    ("Google News — South Asia Security", google("India Pakistan Afghanistan Bangladesh Nepal Sri Lanka conflict security"), "south-asia"),
]
FEEDS = list(dict.fromkeys(FEEDS))
