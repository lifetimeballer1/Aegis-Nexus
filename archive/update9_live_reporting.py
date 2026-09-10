#!/usr/bin/env python3
"""Install resilient, static-first live reporting into Global Pulse."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
LIVE_JSON = ROOT / "data" / "live_articles.json"

CSS = r'''<style id="gp-live-reporting-css">
.gp-reporting-feed{display:grid;gap:10px}.gp-reporting-card{position:relative;padding:13px;background:var(--panel2);border:1px solid var(--line);border-radius:12px;transition:border-color .16s ease,transform .16s ease,background .16s ease}.gp-reporting-card:hover{border-color:#315274;background:#09131e;transform:translateY(-1px)}.gp-reporting-source{display:inline-flex;align-items:center;gap:5px;margin-bottom:7px;padding:4px 7px;border:1px solid rgba(98,160,255,.3);border-radius:6px;background:rgba(98,160,255,.08);color:var(--blue);font-size:9px;font-weight:850;letter-spacing:.07em;text-transform:uppercase}.gp-reporting-title{display:block;margin:2px 0 6px;color:var(--text);font-size:15px;font-weight:850;line-height:1.35}.gp-reporting-title:hover{color:var(--blue)}.gp-reporting-time{display:block;margin-bottom:8px;color:var(--muted);font-size:10px}.gp-reporting-summary{margin:0;color:var(--muted);font-size:11px;line-height:1.55}.gp-reporting-source-name{margin-top:8px;color:var(--muted);font-size:9px}.gp-reporting-action{display:inline-block;margin-top:10px;padding:7px 10px;border:1px solid rgba(98,160,255,.35);border-radius:7px;background:rgba(98,160,255,.08);color:var(--blue);font-size:10px;font-weight:800}.gp-reporting-alert{padding:13px;border:1px solid rgba(255,102,120,.35);border-left:3px solid var(--red);border-radius:11px;background:rgba(255,102,120,.07)}.gp-reporting-alert strong{display:block;margin-bottom:3px;color:var(--red);font-size:11px;letter-spacing:.05em;text-transform:uppercase}.gp-reporting-alert span{color:var(--muted);font-size:10px}.gp-reporting-empty{padding:18px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);text-align:center;font-size:11px}.gp-reporting-count{color:var(--muted);font-size:10px;white-space:nowrap}.gp-reporting-fallback .gp-reporting-card{border-color:rgba(255,200,87,.22)}@media(max-width:720px){.gp-reporting-card{padding:12px}.gp-reporting-title{font-size:14px}.gp-reporting-summary{font-size:11px}}
</style>'''

REPORTING_START = r'''<section id="reporting" class="panel wide" aria-labelledby="latest-reporting-title">
  <div class="section-head">
    <div>
      <h2 id="latest-reporting-title">Latest Reporting</h2>
      <div class="muted">Near-live reporting aggregated from the Global Pulse news pipeline.</div>
    </div>
    <span id="pulse-reporting-count" class="gp-reporting-count" aria-live="polite">—</span>
  </div>
  <div id="pulse-reporting-feed" class="gp-reporting-feed" aria-live="polite" aria-busy="false">'''

REPORTING_END = r'''  </div>
</section>'''


def esc(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return html.escape(text or default, quote=True)


def source_for(article: dict) -> str:
    credit = article.get("credit") or {}
    return esc(credit.get("source") or article.get("source") or article.get("source_name") or article.get("sourceLabel") or "Open-data source")


def link_for(article: dict) -> str:
    credit = article.get("credit") or {}
    raw = article.get("original_link") or article.get("url") or article.get("link") or credit.get("source_url") or ""
    raw = str(raw).strip()
    return html.escape(raw, quote=True) if re.match(r"^https?://[^\s<>\"']+$", raw, re.I) else ""


def initial_cards(limit: int = 5) -> str:
    try:
        payload = json.loads(LIVE_JSON.read_text(encoding="utf-8"))
        articles = payload.get("articles", []) if isinstance(payload, dict) else payload
        if not isinstance(articles, list):
            articles = []
    except (OSError, json.JSONDecodeError):
        articles = []
    cards = []
    for article in articles[:limit]:
        if not isinstance(article, dict):
            continue
        title = esc(article.get("title"), "Untitled report")
        summary = esc(article.get("summary_snippet") or article.get("summary") or article.get("description"), "No summary was provided by the source.")
        published = esc(article.get("published_date") or article.get("time") or article.get("publishedAt") or article.get("timestamp"))
        source = source_for(article)
        link = link_for(article)
        title_html = f'<a class="gp-reporting-title" href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>' if link else f'<div class="gp-reporting-title">{title}</div>'
        action = f'<a class="gp-reporting-action" href="{link}" target="_blank" rel="noopener noreferrer">Read Full Source Report ↗</a>' if link else ""
        cards.append(f'''<article class="gp-reporting-card"><div class="gp-reporting-source">◉ {source}</div>{title_html}<time class="gp-reporting-time" datetime="{published}">Published {published or "time unavailable"}</time><p class="gp-reporting-summary">{summary}</p><div class="gp-reporting-source-name">Source: {source}</div>{action}</article>''')
    return "\n".join(cards) if cards else '<div class="gp-reporting-empty">No active reporting is currently available.</div>'


def patch_index():
    s = INDEX.read_text(encoding="utf-8")
    s = re.sub(r'<script\b[^>]*\bid=["\']gp-auto-refresh["\'][^>]*>.*?</script\s*>', '', s, flags=re.S | re.I)
    s = re.sub(r'<style id="gp-live-reporting-css">.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<script id="gp-live-reporting-config">.*?</script>', '', s)
    s = re.sub(r'<script src="global_pulse_reporting\.js" defer></script>', '', s)
    reporting_html = REPORTING_START + "\n" + initial_cards() + "\n" + REPORTING_END
    s, count = re.subn(r'<section[^>]*id=["\']reporting["\'][\s\S]*?</section>', reporting_html, s, count=1, flags=re.I)
    if count == 0:
        marker = '</main>' if '</main>' in s else '</div>\n</body>'
        s = s.replace(marker, reporting_html + '\n' + marker, 1)
    config = '<script id="gp-live-reporting-config">window.GLOBAL_PULSE_API="";</script>'
    s = s.replace('</head>', CSS + '\n' + config + '\n</head>', 1)
    s = s.replace('</body>', '<script src="global_pulse_reporting.js" defer></script>\n</body>', 1)
    s = s.replace('</head>', '<script id="gp-auto-refresh" type="text/plain"></script>\n</head>', 1)
    if 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js' not in s:
        s = s.replace('</head>', '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n</head>', 1)
    if 'https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js' not in s:
        s = s.replace('</head>', '<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>\n</head>', 1)
    INDEX.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    patch_index()
    print("Update 9 applied: static-first reporting, five-card initial view, idempotent marker, and Leaflet runtime restored.")
