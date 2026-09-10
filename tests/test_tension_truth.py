"""B2 — honest tension freshness.

ensure_brain_groups must not present an un-recomputed tension block as fresh:
it records tensionComputedAt from history.json and flags tensionStale.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ensure_brain_groups_annotates_tension_truth():
    text = (ROOT / 'ensure_brain_groups.py').read_text(encoding='utf-8')
    assert 'annotate_tension_truth' in text
    assert 'tensionComputedAt' in text
    assert 'tensionStale' in text
    assert "snap['updatedAt']=brain['updatedAt']" not in text, 'stale brain timestamp must not stamp the snapshot'


def test_annotate_tension_truth_derives_and_flags(monkeypatch, tmp_path):
    import ensure_brain_groups as eg
    old = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat().replace('+00:00', 'Z')
    (tmp_path / 'history.json').write_text(json.dumps([
        {'updatedAt': old[:-1], 'tension': 41, 'delta': 0, 'scoreVersion': 5},
    ]), encoding='utf-8')
    monkeypatch.setattr(eg, 'DATA', tmp_path)
    snap = eg.annotate_tension_truth({'tension': 41, 'freshness': {'generatedAt': old}})
    assert snap['tensionComputedAt'].startswith(old[:-1][:16]) or snap['tensionComputedAt'] == old[:-1]
    assert snap['tensionStale'] is True

    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    (tmp_path / 'history.json').write_text(json.dumps([
        {'updatedAt': now, 'tension': 41, 'delta': 0, 'scoreVersion': 5},
    ]), encoding='utf-8')
    snap = eg.annotate_tension_truth({'tension': 41})
    assert snap['tensionStale'] is False
