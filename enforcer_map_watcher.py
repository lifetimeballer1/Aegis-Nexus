#!/usr/bin/env python3
"""Keyless watcher for The Enforcer's public YouTube feed.

No YouTube API key is used. The checker tries several public yt-dlp clients,
then the legacy Atom feed. Google My Maps links are stored only as source
references and are not treated as independently verified intelligence.
"""
import json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data"/"enforcer_maps.json"
CHANNEL="https://www.youtube.com/@enforcerofficial/videos"
FEED="https://www.youtube.com/feeds/videos.xml?channel_id=UCM-eRxEc_TutiPIbOS1YYbw"
NS={"a":"http://www.w3.org/2005/Atom","m":"http://search.yahoo.com/mrss/"}
MAP_RE=re.compile(r"https?://(?:www\.)?google\.com/maps/d/(?:[^\s<>'\"]*?/)?(?:edit|viewer)(?:\?[^\s<>'\"]+)?",re.I)
UA="GlobalPulse/1.4"

def clean_url(u): return u.rstrip(".,;:)]}")

def normalize_date(v):
    if isinstance(v,int): return datetime.fromtimestamp(v,timezone.utc).isoformat()
    s=str(v or "")
    if re.fullmatch(r"\d{8}",s): return f"{s[:4]}-{s[4:6]}-{s[6:8]}T00:00:00+00:00"
    return s

def extract_with_client(client):
    import yt_dlp
    opts={"quiet":True,"no_warnings":True,"skip_download":True,"extract_flat":False,"playlistend":20,"socket_timeout":25,"extractor_args":{"youtube":{"player_client":[client]}}}
    with yt_dlp.YoutubeDL(opts) as ydl: info=ydl.extract_info(CHANNEL,download=False)
    videos=[]
    for e in (info.get("entries") or []):
        if not e: continue
        vid=str(e.get("id") or ""); desc=str(e.get("description") or ""); urls=[]
        for u in MAP_RE.findall(desc):
            u=clean_url(u)
            if u not in urls: urls.append(u)
        videos.append({"videoId":vid,"title":str(e.get("title") or ""),"published":normalize_date(e.get("timestamp") or e.get("upload_date")),"videoUrl":"https://www.youtube.com/watch?v="+vid if vid else str(e.get("webpage_url") or ""),"mapCount":len(urls),"mapUrls":urls})
    if not videos: raise RuntimeError("client returned no public videos")
    return videos

def collect_with_rss():
    req=Request(FEED,headers={"User-Agent":UA})
    with urlopen(req,timeout=25) as r: xml=r.read()
    root=ET.fromstring(xml); videos=[]
    for entry in root.findall("a:entry",NS):
        vid=entry.findtext("a:id","",NS).split(":")[-1]; title=entry.findtext("a:title","",NS); published=entry.findtext("a:published","",NS); group=entry.find("m:group",NS); desc=group.findtext("m:description","",NS) if group is not None else ""; urls=[]
        for u in MAP_RE.findall(desc or ""):
            u=clean_url(u)
            if u not in urls: urls.append(u)
        videos.append({"videoId":vid,"title":title,"published":published,"videoUrl":"https://www.youtube.com/watch?v="+vid,"mapCount":len(urls),"mapUrls":urls})
    if not videos: raise RuntimeError("RSS returned no videos")
    return videos

def main():
    videos=None; method=None; errors=[]
    try:
        import yt_dlp  # noqa: F401
        for client in ("tv","web_safari","mweb","android"):
            try:
                videos=extract_with_client(client); method=f"yt-dlp public channel ({client})"; print(f"YouTube client {client}: {len(videos)} videos"); break
            except Exception as e: errors.append(f"{client}: {e}")
    except ImportError as e: errors.append(f"yt-dlp unavailable: {e}")
    if videos is None:
        try: videos=collect_with_rss(); method="YouTube public RSS fallback"
        except Exception as e: errors.append(f"RSS: {e}")
    if videos is None: raise RuntimeError("All public Enforcer checks failed: "+" | ".join(errors))
    existing=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"source":"The Enforcer","channel":"@enforcerofficial","maps":[]}
    by_url={x.get("url"):x for x in existing.get("maps",[]) if x.get("url")}; new_links=0
    for video in videos:
        for u in video.get("mapUrls",[]):
            if u not in by_url:
                new_links+=1; by_url[u]={"url":u,"title":video.get("title",""),"videoUrl":video.get("videoUrl",""),"published":video.get("published",""),"source":"The Enforcer YouTube description","confidence":"SOURCE LINK / UNVERIFIED"}
            else: by_url[u].update({"title":video.get("title",""),"videoUrl":video.get("videoUrl",""),"published":video.get("published","")})
    maps=sorted(by_url.values(),key=lambda x:x.get("published","") or "",reverse=True)[:100]
    existing.update({"updatedAt":datetime.now(timezone.utc).isoformat(),"feedUrl":FEED,"channelUrl":CHANNEL,"maps":maps,"recentVideos":videos[:20],"newMapLinks":new_links,"collectionMethod":method,"checkErrors":errors,"note":"Public YouTube data only; map links are extracted from descriptions and remain source references."})
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding="utf-8",newline="\n")
    print(f"Enforcer watcher: {len(videos)} videos checked, {len(maps)} unique map links, {new_links} new links via {method}")

if __name__=="__main__": main()
