"""B5/B12 — dormant-layer wiring contracts for the canonical refresh."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = (ROOT / 'refresh_pipeline.py').read_text(encoding='utf-8')


def idx(token):
    position = PIPELINE.find(token)
    assert position >= 0, f'refresh_pipeline.py missing {token}'
    return position


def test_dormant_layers_run_before_canonical():
    for token in (
        "'merge_live_news.py'",
        "'build_live_events.py'",
        "'build_event_consistency.py'",
        "'build_event_resolution.py'",
        "'build_source_evidence.py'",
        "'claim_intelligence.py'",
        "'build_event_intelligence.py'",
    ):
        assert idx(token) < idx("'build_canonical_intelligence_v3.py'"), f'{token} must run before canonical'


def test_event_intelligence_after_its_inputs():
    assert idx("'build_source_evidence.py'") < idx("'build_event_intelligence.py'")
    assert idx("'build_event_consistency.py'") < idx("'build_event_intelligence.py'")
    assert idx("'build_live_events.py'") < idx("'build_event_intelligence.py'")


def test_assessment_after_graph_before_brain():
    assert idx("verify_graph(graph)") < idx("'build_intelligence_assessment.py'") < idx("'build_intelligence_brain.py'")


def test_trends_after_strategic_signals():
    assert idx("'build_strategic_signals.py'") < idx("'build_historical_trends.py'")


def test_required_and_manifest_cover_dormant_layers():
    for name in ('live_events.json', 'claims.json', 'source_evidence.json', 'event_intelligence.json',
                 'event_consistency.json', 'event_resolution.json', 'intelligence_assessment.json', 'historical_trends.json'):
        assert f"'{name}'" in PIPELINE, f'{name} missing from refresh pipeline artifact lists'


def test_story_builder_runs_after_brain_validation():
    assert idx("verify_brain(brain)") < idx("'build_brain_stories.py'") < idx("'build_strategic_signals.py'")
    for name in ('brain_stories.json', 'brain_gap_history.json'):
        assert f"'{name}'" in PIPELINE, f'{name} missing from refresh pipeline artifact lists'
    assert idx("'validate_brain_stories.py'") > idx("'build_brain_stories.py'")
    assert idx("'validate_brain_gap_history.py'") > idx("'build_brain_stories.py'")
