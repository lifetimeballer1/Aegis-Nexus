#!/usr/bin/env python3
"""Append-only pipeline run history for the Sources/Health workspace.

Records one entry per canonical refresh (success or failure) to
data/pipeline_history.json so the browser can render a real run-history
table. Outside the refresh manifest (written before these records exist);
entries are capped and corrupt files restart cleanly (last-known-good kept
while readable).
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
HISTORY = DATA / "pipeline_history.json"
LIMIT = 30


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record(*, status: str, started_iso: str, error: str | None = None, limit: int = LIMIT) -> dict:
    DATA.mkdir(exist_ok=True)
    try:
        doc = json.loads(HISTORY.read_text(encoding="utf-8"))
        runs = doc.get("runs") if isinstance(doc, dict) and isinstance(doc.get("runs"), list) else []
    except Exception:
        runs = []
    now = utcnow()
    try:
        started = datetime.fromisoformat(str(started_iso).replace("Z", "+00:00"))
        duration = max(0.0, (datetime.now(timezone.utc) - started).total_seconds())
    except Exception:
        duration = 0.0
    entry = {
        "runId": os.environ.get("GITHUB_RUN_ID") or f"local-{now}",
        "trigger": os.environ.get("GITHUB_EVENT_NAME") or "manual",
        "startedAt": started_iso,
        "finishedAt": now,
        "durationSeconds": round(duration, 1),
        "status": status,
    }
    if error:
        entry["error"] = str(error)[:240]
    runs = [entry] + [r for r in runs if isinstance(r, dict)][: max(1, limit) - 1]
    doc = {"version": 1, "updatedAt": now, "runs": runs}
    HISTORY.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return entry


if __name__ == "__main__":
    raise SystemExit("import pipeline_history and call record(); no CLI")
