"""Phase 8 — pipeline hardening contracts.

Registry must rebuild LF-safe from the catalog in loader shape; failover
state must refresh from collector telemetry with validator-required shape
and never touch snapshot.updatedAt; manifest covers the pipeline-written
feeds; the operational gate watches sources.json freshness.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sources_registry_rebuilds_from_catalog(tmp_path, monkeypatch):
    import build_sources_registry as reg

    monkeypatch.setattr(reg, "DATA", tmp_path)
    assert reg.main() == 0
    raw = (tmp_path / "sources.json").read_bytes()
    assert b"\r" not in raw
    doc = json.loads(raw.decode("utf-8"))
    assert doc["updatedAt"] and isinstance(doc["feeds"], list) and len(doc["feeds"]) >= 20
    for feed in doc["feeds"]:
        assert feed["name"] and feed["url"] and feed["domain"] and feed.get("type")
    import news_feed_db
    sources = news_feed_db.load_sources()
    assert sources, "registry must stay loader-compatible"


def test_failover_state_refreshes_without_touching_updated_at(tmp_path, monkeypatch):
    import build_failover_state as fo

    monkeypatch.setattr(fo, "DATA", tmp_path)
    live = {"updatedAt": "2026-09-09T00:00:00Z", "feedsChecked": 4,
            "sourceResults": [{"name": "a", "httpOk": True, "mode": "native"},
                              {"name": "b", "httpOk": False, "mode": "failed"},
                              {"name": "c", "httpOk": True, "mode": "gdelt-domain-fallback"}]}
    snap = {"updatedAt": "2026-09-09T00:00:00Z", "stories": []}
    (tmp_path / "live_status.json").write_text(json.dumps(live), encoding="utf-8")
    (tmp_path / "snapshot.json").write_text(json.dumps(snap), encoding="utf-8")
    assert fo.main() == 0
    out = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert out["updatedAt"] == "2026-09-09T00:00:00Z"
    assert isinstance(out["sourceFailover"].get("replacements"), list)
    state = out["failoverState"]
    assert (state["total"], state["down"], state["healthy"]) == (4, 1, 3)
    assert state["fallbacks"] == 1 and state["failedSources"] == ["b"]
    assert b"\r" not in (tmp_path / "snapshot.json").read_bytes()


def test_manifest_scope_and_pipeline_hooks():
    text = (ROOT / "refresh_pipeline.py").read_text(encoding="utf-8")
    assert "'live_status.json'" in text or '"live_status.json"' in text
    assert "'what_changed.json'" in text or '"what_changed.json"' in text
    assert "build_sources_registry.py" in text
    assert "build_failover_state.py" in text
    op = (ROOT / "validate_operational_health.py").read_text(encoding="utf-8")
    assert "'sources.json'" in op or '"sources.json"' in op
