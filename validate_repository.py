#!/usr/bin/env python3
"""Repository-level integrity checks for Global Pulse.

This complements syntax checks by catching stale browser assets, duplicate HTML
IDs/scripts, broken local references, and malformed JSON artifacts.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"


class IdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.script_srcs: list[str] = []
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        amap = {k.lower(): v for k, v in attrs}
        value = amap.get("id")
        if value:
            self.ids.append(value)
        for key in ("src", "href"):
            value = amap.get(key)
            if value:
                self.refs.append(value)
        if tag.lower() == "script" and amap.get("src"):
            self.script_srcs.append(amap["src"] or "")


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    parser = IdParser()
    parser.feed(html)
    parser.close()

    missing: list[str] = []
    for ref in parser.refs:
        if ref.startswith(("http://", "https://", "//", "data:", "#")):
            continue
        local = ref.split("?", 1)[0].split("#", 1)[0]
        if local and not (ROOT / local).exists():
            missing.append(local)
    if missing:
        raise SystemExit("Missing local browser assets: " + ", ".join(sorted(set(missing))))

    duplicates = sorted({x for x in parser.ids if parser.ids.count(x) > 1})
    if duplicates:
        raise SystemExit("Duplicate HTML ids: " + ", ".join(duplicates))

    normalized = [x.split("?", 1)[0] for x in parser.script_srcs]
    duplicate_scripts = sorted({x for x in normalized if normalized.count(x) > 1})
    if duplicate_scripts:
        raise SystemExit("Duplicate script inclusions: " + ", ".join(duplicate_scripts))

    json_paths = [Path("site.webmanifest"), *sorted((ROOT / "data").glob("*.json"))]
    for path in json_paths:
        json.loads(path.read_text(encoding="utf-8"))

    retired = [
        "global_pulse_graph_stable.js",
        "global_pulse_graph_v3.js",
        "global_pulse_graph_pro.js",
        "intelligence_web_v1.js",
        "global_pulse_intelligence.css",
        "global_pulse_list_density.css",
        "global_pulse_phase3.css",
        "install_breaking_alerts.py",
        "install_claim_intelligence.py",
        "install_commander_center.py",
        "install_health_finalizer.py",
        "install_intelligence_assessment.py",
        "install_intelligence_web.py",
        "install_live_events.py",
        "install_map_age_filter.py",
        "install_map_clustering.py",
        "install_map_v3.py",
        "install_qa_hardening.py",
        "run_snapshot_resilient.py",
        "run_snapshot_counter_cartel.py",
        "build_canonical_intelligence.py",
    ]
    leftovers = [x for x in retired if (ROOT / x).exists()]
    if leftovers:
        raise SystemExit("Retired renderer files remain: " + ", ".join(leftovers))

    print("REPOSITORY INTEGRITY PASSED")
    print(f"Local browser references checked: {len([r for r in parser.refs if not r.startswith(('http://','https://','//','data:','#'))])}")
    print(f"JSON artifacts checked: {len(json_paths)}")
    print("No duplicate real HTML ids or browser script inclusions detected.")


if __name__ == "__main__":
    main()
