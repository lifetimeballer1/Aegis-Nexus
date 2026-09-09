#!/usr/bin/env python3
"""Record structured per-contract validation results for the browser.

Re-runs the read-only repository validators (the same gates CI enforces),
captures pass/fail plus a short evidence tail, and writes
data/validation_results.json for the Sources/Validation workspace.
Invoked at the END of refresh_pipeline.py after all gates pass, so a
failing gate still aborts the refresh before this file is rewritten
(fail-closed preserved). Outside the refresh manifest (written earlier).
"""
from __future__ import annotations
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "validation_results.json"

# (contract label, command argv). Read-only validators only; each <1s local.
VALIDATORS: tuple[tuple[str, list[str]], ...] = (
    ("Source health gate", [sys.executable, "validate_source_health.py"]),
    ("Data resilience gate", [sys.executable, "validate_data_resilience.py"]),
    ("Data resilience + manifest gate", [sys.executable, "validate_data_resilience.py", "--require-manifest"]),
    ("Intelligence Web evidence contract", [sys.executable, "validate_intelligence_graph.py"]),
    ("Intelligence Brain contract", [sys.executable, "validate_intelligence_brain.py"]),
    ("Action intelligence contract", [sys.executable, "validate_action_intelligence.py"]),
    ("Operational health gate", [sys.executable, "validate_operational_health.py"]),
    ("Repository integrity gate", [sys.executable, "validate_repository.py"]),
    ("Performance / mobile gate", [sys.executable, "validate_performance.py"]),
    ("Security / privacy gate", [sys.executable, "validate_security.py"]),
    ("Event resolution gate", [sys.executable, "validate_event_resolution.py"]),
    ("Pipeline schema gate", [sys.executable, "validate_pipeline.py"]),
)


def tail(text: str, lines: int = 3, limit: int = 240) -> str:
    kept = [ln.strip() for ln in (text or "").splitlines() if ln.strip()][-lines:]
    scrubbed = " | ".join(kept).replace(str(ROOT), "").replace(str(DATA), "data")
    return scrubbed[:limit]


def main() -> int:
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    results = []
    for contract, cmd in VALIDATORS:
        begun = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
            passed = proc.returncode == 0
            detail = tail(proc.stdout) if passed else (tail(proc.stderr) or tail(proc.stdout) or f"exit {proc.returncode}")
        except Exception as exc:
            passed, detail = False, f"{type(exc).__name__}: {exc}"[:240]
        results.append({
            "contract": contract,
            "command": " ".join(cmd[1:]),
            "passed": passed,
            "detail": detail,
            "durationMs": int((time.monotonic() - begun) * 1000),
        })
    passed_n = sum(1 for r in results if r["passed"])
    doc = {
        "version": 1,
        "updatedAt": started,
        "summary": {"run": len(results), "passed": passed_n, "failed": len(results) - passed_n, "blocked": 0},
        "results": results,
    }
    DATA.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"VALIDATION RESULTS: {passed_n}/{len(results)} passed -> {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
