"""The snapshot gate must validate the same geographic artifact as the browser."""
import json
from pathlib import Path
import shutil
import subprocess
import sys


def run_gate(tmp_path, markers):
    script = tmp_path / 'validate_pipeline.py'
    shutil.copyfile(Path(__file__).resolve().parents[1] / script.name, script)
    data = tmp_path / 'data'
    data.mkdir()
    # Unlocated reports are legitimate upstream inputs, not published map points.
    (data / 'snapshot.json').write_text(json.dumps({'stories': [], 'conflicts': [], 'markers': [{'title': 'Unlocated report'}]}))
    (data / 'map_points.json').write_text(json.dumps({'markers': markers}))
    # A stale root artifact must never mask corruption in the canonical feed.
    (tmp_path / 'snapshot.json').write_text('{}')
    return subprocess.run([sys.executable, str(script)], cwd=tmp_path.parent, capture_output=True, text=True)


def test_uses_canonical_map_feed_from_any_working_directory(tmp_path):
    result = run_gate(tmp_path, [{'lat': 10, 'lng': 20}])
    assert result.returncode == 0, result.stdout
    assert '1 map markers' in result.stdout


def test_rejects_invalid_published_coordinates(tmp_path):
    result = run_gate(tmp_path, [{'lat': 91, 'lng': 20}])
    assert result.returncode != 0
    assert 'latitude out of range' in result.stdout
