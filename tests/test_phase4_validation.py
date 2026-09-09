"""Phase 4 — validation results + run history contracts.

New artifacts must be LF-safe JSON outside the byte-exact manifest;
history recording must cap runs and survive corrupt files; the frontend
must bind the new feeds with honest empty states.
"""
import json
from pathlib import Path

import pipeline_history
from pipeline_history import HISTORY, record
import build_validation_results as bvr

ROOT = Path(__file__).resolve().parents[1]


def test_history_record_is_lf_safe_capped_and_recovers(tmp_path, monkeypatch):
    target = tmp_path / "pipeline_history.json"
    monkeypatch.setattr(pipeline_history, "HISTORY", target)
    monkeypatch.setattr(pipeline_history, "DATA", tmp_path)
    for i in range(35):
        record(status="Success", started_iso="2026-09-09T00:00:00Z", limit=30)
    doc = json.loads(target.read_text(encoding="utf-8"))
    assert len(doc["runs"]) == 30
    raw = target.read_bytes()
    assert b"\r" not in raw
    assert doc["runs"][0]["status"] == "Success"
    target.write_bytes(b"{corrupt")
    entry = record(status="Failed", started_iso="2026-09-09T00:00:00Z", error="boom")
    assert entry["status"] == "Failed" and entry["error"] == "boom"
    assert len(json.loads(target.read_text(encoding="utf-8"))["runs"]) == 1


def test_validation_contracts_reference_real_scripts():
    assert len(bvr.VALIDATORS) >= 10
    for contract, cmd in bvr.VALIDATORS:
        assert contract and isinstance(cmd, list)
        script = cmd[-1] if cmd[-1].endswith(".py") else cmd[-2]
        assert (ROOT / script).is_file(), f"validator missing: {script}"


def test_pipeline_hooks_and_manifest_scope():
    text = (ROOT / "refresh_pipeline.py").read_text(encoding="utf-8")
    assert "build_validation_results.py" in text
    assert "pipeline_history import record" in text
    assert "status='Failed'" in text and "status='Success'" in text
    assert "validation_results.json" not in text.split("MANIFEST_ARTIFACTS")[1].split(")")[0]


def test_frontend_binds_validation_history_flow_and_credibility():
    config = (ROOT / "js/core/config.js").read_text(encoding="utf-8")
    assert "./data/validation_results.json" in config
    assert "./data/pipeline_history.json" in config
    state = (ROOT / "js/core/state.js").read_text(encoding="utf-8")
    assert "validationResults" in state and "pipelineHistory" in state
    fetch = (ROOT / "js/core/fetch.js").read_text(encoding="utf-8")
    assert "validationResults" in fetch and "pipelineHistory" in fetch
    status = (ROOT / "js/modules/status.js").read_text(encoding="utf-8")
    for token in ("Validation &amp; Data Contracts", "Pipeline Run History", "Refresh Pipeline Health",
                  "credibility", "fallback", "No run history yet", "No validation run recorded yet"):
        assert token in status, f"status workspace missing {token}"
    assert "Generate with AI" not in status
