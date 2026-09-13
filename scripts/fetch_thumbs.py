#!/usr/bin/env python3
"""Build-time story thumbnail resolver for Aegis-Nexus GUI views.

Reads fixture headlines (data/gui-fixtures.json) + live articles
(data/live_articles.json), resolves each story to a source page URL,
extracts og:image / twitter:image (fallback: first plausible <img>),
downloads capped-size images to assets/thumbs/<slug>.<ext>, and writes
assets/thumbs/manifest.json (slug -> file).

Also generates dark-theme SVG category fallback art
(assets/thumbs/fallback-<category>.svg) so cards never show a broken image.

Stdlib only. Every fetch is wrapped in try/except: one bad story never
stops the run. Caps: 400KB per file, ~5MB total.
"""
import html
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib import request as urlreq
from urllib.parse import urljoin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMB_DIR = os.path.join(ROOT, "assets", "thumbs")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
PAGE_TIMEOUT = 8
MAX_TOTAL = 5 * 1024 * 1024
MAX_FILE = 400 * 1024
MAX_HTML = 300 * 1024
WORKERS = 6
LIVE_TOP_N = 40
MAX_NEW_PER_RUN = 20

CATS = ["geopolitical", "economic", "indo-pacific", "domestic", "general",
        "generic", "regional", "cartel", "international", "news",
        "diplomatic", "conflict", "political"]


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")[:48]


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def fallback_for(cat):
    c = re.sub(r"[^a-z-]", "", str(cat or "general").lower())
    if c in CATS:
        return c
    if re.search(r"conflict|security", c):
        return "conflict"
    if "cartel" in c:
        return "cartel"
    if re.search(r"econom|market|trade", c):
        return "economic"
    if c == "us-politics":
        return "domestic"
    if re.search(r"politic|election", c):
        return "political"
    if re.search(r"china|asia|pacific|indo", c):
        return "indo-pacific"
    if re.search(r"geopolit|middle-east|europe|africa|americas|world", c):
        return "geopolitical"
    if re.search(r"region|southcom", c) or c == "live":
        return "regional"
    if "diploma" in c:
        return "diplomatic"
    if "intern" in c:
        return "international"
    return "generic"


def load_json(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def collect_stories():
    """Return list of (title, category) covering fixture stories."""
    stories = []
    try:
        fx = load_json("data/gui-fixtures.json")
        hl = fx.get("headlines", {}) or {}
        for s in hl.get("stories", []) or []:
            if isinstance(s, dict) and s.get("title"):
                stories.append((s["title"], s.get("type", "general")))
        for d in hl.get("topDevelopments", []) or []:
            if isinstance(d, dict) and d.get("title"):
                stories.append((d["title"], d.get("category", "general")))
        for e in hl.get("events", []) or []:
            if isinstance(e, dict) and e.get("title"):
                stories.append((e["title"], e.get("category", "general")))
    except Exception as ex:
        print("fixtures read failed: %s" % ex, file=sys.stderr)
    return stories


def collect_live():
    """Return list of (title, category, url) for newest live articles."""
    out = []
    try:
        d = load_json("data/live_articles.json")
        arts = d.get("articles", []) or []
        for a in arts[:LIVE_TOP_N]:
            if isinstance(a, dict) and a.get("title") and a.get("url", "").startswith("http"):
                out.append((a["title"], a.get("category", "general"), a["url"]))
    except Exception as ex:
        print("live articles read failed: %s" % ex, file=sys.stderr)
    return out


def resolve_url(title, live):
    """Match a fixture title to a live article URL (mirrors matchContext)."""
    n = norm(title)
    if not n:
        return None
    key = n[:24]
    for lt, _lc, lu in live:
        m = norm(lt)
        if not m:
            continue
        if key in m or m[:24] in n:
            return lu
    return None


def get_html(url):
    req = urlreq.Request(url, headers=UA)
    with urlreq.urlopen(req, timeout=PAGE_TIMEOUT) as r:
        ctype = (r.headers.get("Content-Type", "") or "").lower()
        if "html" not in ctype and "xml" not in ctype and "text" not in ctype:
            return None, url
        raw = r.read(MAX_HTML + 1)
    try:
        return raw[:MAX_HTML].decode("utf-8", "replace"), r.geturl()
    except Exception:
        return None, url


def meta_attrs(tag):
    return dict((k.lower(), html.unescape(v))
                for k, v in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", tag))


def extract_image(page_html, page_url):
    if not page_html:
        return None
    for tag in re.findall(r"<meta[^>]+>", page_html[:MAX_HTML], re.I):
        a = meta_attrs(tag)
        prop = (a.get("property", "") or a.get("name", "")).lower()
        if prop in ("og:image", "twitter:image", "twitter:image:src") \
                and a.get("content", "").startswith("http"):
            return a["content"].strip()
    first = None
    for tag in re.findall(r"<img[^>]+>", page_html[:MAX_HTML], re.I):
        a = meta_attrs(tag)
        src = (a.get("src", "") or "").strip()
        if not src.startswith("http") and not src.startswith("//"):
            continue
        low = src.lower()
        if any(b in low for b in ("logo", "sprite", "icon", "avatar", "1x1",
                                  "pixel", "ads/", ".svg")):
            continue
        try:
            w = int(a.get("width", "0") or 0)
        except ValueError:
            w = 0
        full = urljoin(page_url, src)
        if w >= 300:
            return full
        if first is None:
            first = full
    return first


EXT_BY_CTYPE = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
                "image/webp": ".webp", "image/gif": ".gif"}
MAGIC = (b"\xff\xd8", b"\x89PNG", b"GIF8", b"RIFF")


def download_image(url):
    req = urlreq.Request(url, headers=UA)
    with urlreq.urlopen(req, timeout=PAGE_TIMEOUT) as r:
        ctype = (r.headers.get("Content-Type", "") or "").split(";")[0].strip().lower()
        if not ctype.startswith("image/"):
            return None, None
        length = r.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > MAX_FILE:
            return None, None
        data = r.read(MAX_FILE + 1)
    if len(data) > MAX_FILE or not data.startswith(MAGIC):
        return None, None
    return data, EXT_BY_CTYPE.get(ctype, ".jpg")


FALLBACK_STYLE = {
    "geopolitical": ("#5aa9ff", "◈"), "economic": ("#4ade80", "▲"),
    "indo-pacific": ("#22d3ee", "≋"), "domestic": ("#f59e0b", "⌂"),
    "general": ("#94a3b8", "◉"), "generic": ("#64748b", "◇"),
    "regional": ("#a78bfa", "◎"), "cartel": ("#f87171", "◆"),
    "international": ("#60a5fa", "❖"), "news": ("#fbbf24", "☰"),
    "diplomatic": ("#34d399", "✦"), "conflict": ("#ef4444", "✖"),
    "political": ("#e879f9", "★"),
}


def write_fallbacks():
    os.makedirs(THUMB_DIR, exist_ok=True)
    for cat in CATS:
        accent, glyph = FALLBACK_STYLE[cat]
        svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='192' height='144' viewBox='0 0 192 144'>"
               "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
               "<stop offset='0' stop-color='#0d1526'/><stop offset='1' stop-color='#16233d'/>"
               "</linearGradient></defs>"
               "<rect width='192' height='144' fill='url(#g)'/>"
               "<g stroke='%s' stroke-opacity='0.15'>"
               "<path d='M0 36 H192 M0 72 H192 M0 108 H192 M48 0 V144 M96 0 V144 M144 0 V144'/></g>"
               "<circle cx='96' cy='60' r='30' fill='%s' fill-opacity='0.16'/>"
               "<text x='96' y='73' text-anchor='middle' font-size='32' fill='%s'>%s</text>"
               "<text x='96' y='118' text-anchor='middle' font-family='sans-serif' font-size='11' "
               "letter-spacing='2' fill='#8fa1bd'>%s</text>"
               "<rect x='0.5' y='0.5' width='191' height='143' fill='none' stroke='%s' stroke-opacity='0.35'/>"
               "</svg>" % (accent, accent, accent, glyph, cat.upper(), accent))
        with open(os.path.join(THUMB_DIR, "fallback-%s.svg" % cat), "w", encoding="utf-8") as f:
            f.write(svg)


def fetch_one(item):
    title, cat, url = item
    try:
        page_html, final_url = get_html(url)
        img = extract_image(page_html, final_url)
        if not img:
            return (title, cat, None, "no-image")
        data, ext = download_image(img)
        if not data:
            return (title, cat, None, "dl-fail")
        return (title, cat, (data, ext), None)
    except Exception as ex:
        return (title, cat, None, "%s: %s" % (type(ex).__name__, str(ex)[:80]))


def main():
    os.makedirs(THUMB_DIR, exist_ok=True)
    write_fallbacks()
    # Incremental mode: preserve existing manifest so re-runs only fetch NEW slugs.
    existing_map = {}
    try:
        with open(os.path.join(THUMB_DIR, "manifest.json"), encoding="utf-8") as _mf:
            _em = (json.load(_mf).get("map") or {})
            if isinstance(_em, dict):
                existing_map = _em
    except Exception:
        existing_map = {}
    live = collect_live()
    jobs, seen = [], set()
    for title, cat in collect_stories():
        slug = slugify(title)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        url = resolve_url(title, live)
        if url:
            jobs.append((title, cat, url))
    for title, cat, url in live:
        slug = slugify(title)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        jobs.append((title, cat, url))
    # Incremental: skip slugs already manifested with file on disk; newest (live) first; cap per-run.
    _new_jobs, _live_urls = [], set(_u for _t, _c, _u in live)
    for _t, _c, _u in jobs:
        _s = slugify(_t)
        _f = existing_map.get(_s)
        if _f and os.path.isfile(os.path.join(THUMB_DIR, _f)):
            continue
        _new_jobs.append((_t, _c, _u))
    _new_jobs.sort(key=lambda _j: (0 if _j[2] in _live_urls else 1))
    jobs = _new_jobs[:MAX_NEW_PER_RUN]
    results = []
    if jobs:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            results = list(pool.map(fetch_one, jobs))
    mapping = dict(existing_map)
    try:
        total_bytes = sum(os.path.getsize(os.path.join(THUMB_DIR, _f)) for _f in mapping.values() if os.path.isfile(os.path.join(THUMB_DIR, _f)))
    except Exception:
        total_bytes = 0
    real = sum(1 for _f in mapping.values() if os.path.isfile(os.path.join(THUMB_DIR, _f)))
    _new_real = 0
    skips = {"no-image": 0, "dl-fail": 0, "over-cap": 0}
    for title, cat, payload, err in results:
        slug = slugify(title)
        if payload is None:
            skips["no-image" if err == "no-image" else "dl-fail"] += 1
            continue
        data, ext = payload
        if total_bytes + len(data) > MAX_TOTAL:
            skips["over-cap"] += 1
            continue
        fname = slug + ext
        try:
            with open(os.path.join(THUMB_DIR, fname), "wb") as f:
                f.write(data)
        except Exception as ex:
            print("write failed %s: %s" % (fname, ex), file=sys.stderr)
            continue
        mapping[slug] = fname
        real += 1
        _new_real += 1
        total_bytes += len(data)
    _all_stories = len(set(list(seen) + list(existing_map.keys())))
    manifest = {"_meta": {"real": real, "stories": _all_stories, "newReal": _new_real,
                          "kbTotal": round(total_bytes / 1024, 1),
                          "note": "slug->file; missing slug = use fallback-<category>.svg"},
                "map": mapping}
    with open(os.path.join(THUMB_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print("THUMB_SUMMARY " + json.dumps({
        "stories_seen": len(seen), "fetch_jobs": len(jobs), "real_thumbs": real,
        "fallbacks": len(seen) - real, "kb_total": round(total_bytes / 1024, 1),
        "files": len(mapping), "skip": skips}))


if __name__ == "__main__":
    main()
