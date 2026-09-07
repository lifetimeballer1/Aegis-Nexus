#!/usr/bin/env python3
"""Validate the Phase 5 data-resilience contract without inventing data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REQUIRED = (
    "snapshot.json",
    "sources.json",
    "live_articles.json",
    "intelligence_graph.json",
    "intelligence_brain.json",
)


def read_json(name: str):
    path = DATA / name
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"RESILIENCE GATE FAILED: missing/empty {name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"RESILIENCE GATE FAILED: invalid JSON in {name}: {exc}") from exc


def validate_manifest(require_manifest: bool) -> None:
    # During refresh, snapshot.json is intentionally rewritten several times
    # before the final manifest is produced. A pre-refresh manifest is therefore
    # expected to be stale and must never be used as a mid-pipeline failure gate.
    if not require_manifest:
        print("PASS: manifest check deferred until final refresh stage")
        return

    manifest_path = DATA / "refresh_manifest.json"
    if not manifest_path.is_file() or manifest_path.stat().st_size == 0:
        raise SystemExit("RESILIENCE GATE FAILED: refresh manifest missing")

    manifest = read_json("refresh_manifest.json")
    artifacts = manifest.get("artifacts") or {}
    for name in REQUIRED:
        meta = artifacts.get(name)
        path = DATA / name
        if not meta or not path.is_file() or not meta.get("sha256"):
            raise SystemExit(f"RESILIENCE GATE FAILED: manifest entry missing for {name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != meta["sha256"]:
            raise SystemExit(f"RESILIENCE GATE FAILED: manifest hash mismatch for {name}")
    print("PASS: refresh manifest hashes")


def validate_graph_contract() -> None:
    # Keep the dedicated Intelligence Web contract validator on the canonical
    # refresh path without duplicating its node/edge rules here.
    from validate_intelligence_graph import main as validate_graph
    try:
        validate_graph()
    except AssertionError as exc:
        raise SystemExit(f"RESILIENCE GATE FAILED: intelligence graph contract: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        help="Require and verify the final refresh manifest; use after the pipeline writes it.",
    )
    args = parser.parse_args()

    for name in REQUIRED:
        read_json(name)

    snapshot = read_json("snapshot.json")
    market = snapshot.get("marketData") or {}
    indicators = market.get("indicators") or []
    if market.get("noApiKey") is not True:
        raise SystemExit("RESILIENCE GATE FAILED: market layer must remain keyless")
    if len(indicators) < 20:
        raise SystemExit(f"RESILIENCE GATE FAILED: market indicators={len(indicators)} < 20")
    invalid = [
        x.get("symbol")
        for x in indicators
        if not isinstance(x, dict) or not x.get("symbol") or float(x.get("price") or 0) <= 0
    ]
    if invalid:
        raise SystemExit(f"RESILIENCE GATE FAILED: invalid/non-positive market quotes: {invalid[:8]}")

    failover = snapshot.get("sourceFailover")
    state = snapshot.get("failoverState")
    if not isinstance(failover, dict) or not isinstance(failover.get("replacements"), list):
        raise SystemExit("RESILIENCE GATE FAILED: source failover provenance missing")
    if not isinstance(state, dict):
        raise SystemExit("RESILIENCE GATE FAILED: source failover state missing")

    stories = snapshot.get("stories")
    if not isinstance(stories, list) or not stories:
        raise SystemExit("RESILIENCE GATE FAILED: snapshot stories missing")
    for story in stories:
        if not isinstance(story, dict):
            raise SystemExit("RESILIENCE GATE FAILED: malformed story record")
        if not (story.get("url") or story.get("title")):
            raise SystemExit("RESILIENCE GATE FAILED: story without identity/provenance")

    live = read_json("live_articles.json")
    if not isinstance(live.get("articles"), list) or not live.get("articles"):
        raise SystemExit("RESILIENCE GATE FAILED: live article artifact is empty")

    validate_graph_contract()
    validate_manifest(args.require_manifest)

    print("PASS: Phase 5 data resilience gate")
    print(
        f"stories={len(stories)} liveArticles={len(live['articles'])} "
        f"marketIndicators={len(indicators)} failoverRecords={len(failover['replacements'])}"
    )
    print(
        f"failoverHealthy={state.get('healthy')} failoverDown={state.get('down')} "
        f"fallbackCount={state.get('fallbacks')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())