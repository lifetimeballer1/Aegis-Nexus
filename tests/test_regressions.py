from pathlib import Path
import re
import json

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('headline,expected_targets', [
    ('China Targets Japanese Chemical Imports in Anti-Dumping Move.', ['japan']),
    ('China Targets Japanese Chemical Imports in Anti-Dumping Move - Devdiscourse', ['japan']),
    ('China reviews trade policy. Japan reports economic growth.', []),
])
def test_actor_target_repair_uses_event_evidence(tmp_path, monkeypatch, headline, expected_targets):
    import repair_actor_target_roles as repair
    import enrich_semantic_relationships as semantic

    canonical = tmp_path / 'canonical.json'
    live = tmp_path / 'live.json'
    event = {'id': 'event', 'event_type': 'trade_action', 'actor_ids': ['china', 'japan'],
             'target_ids': [], 'evidence_ids': ['source']}
    document = {'entities': [
        {'id': 'china', 'canonical_name': 'China'},
        {'id': 'japan', 'canonical_name': 'Japan', 'aliases': ['Japanese']},
    ], 'events': [event], 'evidence': [{'id': 'source', 'url': 'https://example.test/event'}],
        'relationships': []}
    canonical.write_text(json.dumps(document), encoding='utf-8')
    live.write_text(json.dumps({'articles': [
        {'url': 'https://example.test/event', 'title': headline, 'summary_snippet': headline},
        {'url': 'https://example.test/unrelated', 'title': 'China Targets Japanese Chemical Imports.'},
    ]}), encoding='utf-8')
    for module in (repair, semantic):
        monkeypatch.setattr(module, 'PATH', canonical)
        monkeypatch.setattr(module, 'LIVE', live)
    assert repair.main() == 0
    repaired = json.loads(canonical.read_text(encoding='utf-8'))['events'][0]
    assert repaired['target_ids'] == expected_targets
    assert repaired['actor_ids'] == (['china'] if expected_targets else ['china', 'japan'])
    assert repaired['evidence_ids'] == ['source']
    assert semantic.main() == 0
    relationships = json.loads(canonical.read_text(encoding='utf-8'))['relationships']
    if expected_targets:
        assert len(relationships) == 1
        relationship = relationships[0]
        assert relationship['source_entity_id'] == 'china'
        assert relationship['target_entity_id'] == 'japan'
        assert relationship['event_ids'] == ['event']
        assert relationship['evidence_ids'] == ['source']
    else:
        assert relationships == []


def test_map_conflict_filter_has_canonical_classifier_and_rerender():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert "filter='all'" in text
    assert "filter!=='all'" in text
    assert "filter==='conflict'&&k==='conflicts'" in text
    assert re.search(r'cartel|organized.?crime|narco', text)
    assert re.search(r'cfr|conflict|military|war|attack|strike', text, re.I)
    assert 'renderMap' in text
    assert 'window.renderMap' not in text


def test_canonical_aliases_and_roles_survive_production_repair_chain(tmp_path, monkeypatch):
    import build_canonical_intelligence_v3 as builder
    import repair_strategic_targets as strategic
    import repair_actor_target_roles as roles
    import enrich_semantic_relationships as semantic

    live = tmp_path / 'live.json'
    canonical = tmp_path / 'canonical.json'
    headlines = [
        ('Japan reports growth', ''),
        ('China Targets Japanese Chemical Imports in Anti-Dumping Move - Devdiscourse',
         'China Targets Japanese Chemical Imports in Anti-Dumping Move Devdiscourse'),
        ('No bailouts for Jaguar Land Rover amid reports of thousands of job cuts, says minister',
         'Carmaker, which is battling Trump tariffs and Chinese competitors, faces talks with union leaders and government '
         'The government has signalled that it will not invest taxpayers money to limit job losses at Jaguar Land Rover (JLR), '
         'after it emerged that the UK biggest carmaker is planning up to 4,000 redundancies.'),
    ]
    articles = [{'url': f'https://example.test/{i}', 'title': title,
                 'summary_snippet': summary, 'published_date': '2026-09-07T07:33:53+00:00'}
                for i, (title, summary) in enumerate(headlines)]
    live.write_text(json.dumps({'articles': articles}), encoding='utf-8')
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    monkeypatch.setattr(builder, 'INPUT', live)
    monkeypatch.setattr(builder, 'OUTPUT', canonical)
    monkeypatch.setattr(strategic, 'CANONICAL', canonical)
    for module in (strategic, roles, semantic):
        monkeypatch.setattr(module, 'LIVE', live)
    for module in (roles, semantic):
        monkeypatch.setattr(module, 'PATH', canonical)
    for stage in (builder, strategic, roles, semantic):
        assert stage.main() == 0
    document = json.loads(canonical.read_text(encoding='utf-8'))
    entities = {e['canonical_name']: e for e in document['entities']}
    china, japan = entities['China']['id'], entities['Japan']['id']
    assert 'japanese' in entities['Japan']['aliases']
    trade = next(e for e in document['events'] if e['title'] == headlines[1][0])
    assert trade['actor_ids'] == [china]
    assert trade['target_ids'] == [japan]
    assert any(r['source_entity_id'] == china and r['target_entity_id'] == japan
               and trade['id'] in r['event_ids'] and r['evidence_ids'] == trade['evidence_ids']
               for r in document['relationships'])
    layoffs = [e for e in document['events'] if e['title'] == headlines[2][0]]
    assert all(not e['target_ids'] for e in layoffs if e['event_type'] == 'diplomatic_action')


def test_map_and_brain_share_canonical_artifact_and_node_identity():
    map_text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    config_text = (ROOT / 'js/core/config.js').read_text(encoding='utf-8')
    brain = (ROOT / 'data/intelligence_brain.json').read_text(encoding='utf-8')
    assert 'intelligenceBrain' in config_text
    assert "'intelligenceBrain'" in map_text
    assert 'mapData?.brain' in map_text
    assert 'sourceBackedOnly===true' in map_text
    assert 'nodeId:String(n.id)' in map_text
    assert 'brainEdgesFor' in map_text
    assert '"complete":true' in brain
    assert '"sourceBackedOnly":true' in brain
    assert '"consolidated":true' in brain


def test_map_renders_only_geographic_brain_relationships_and_can_toggle_them():
    text = (ROOT / 'js/modules/map.js').read_text(encoding='utf-8')
    assert 'renderBrainLinks' in text
    assert 'L.polyline' in text
    assert 'byId.get(String(e.source))' in text
    assert 'byId.get(String(e.target))' in text
    assert "String(e.source)===String(e.target)" in text
    assert 'gpMapBrainLinks' in text
    assert 'gp.mapBrainLinks' in text
    assert "if(!a||!b" in text


def test_live_news_feed_schema_normalizes_to_browser_story_shape():
    import merge_live_news as merger
    item = {'url':'https://example.test/story','title':'Test conflict report','published_date':'2026-09-05T12:00:00+00:00','summary_snippet':'A test report.','source_name':'Example News','source_type':'news'}
    story = merger.normalize_article(item)
    assert story['url'] == item['url']; assert story['source'] == item['url']; assert story['sourceLabel'] == 'Example News'; assert story['sourceName'] == 'Example News'; assert story['sourceType'] == 'news'; assert story['published_date'] == item['published_date']; assert story['time'] == item['published_date']; assert story['title'] == item['title']


def test_live_news_timestamp_normalization_is_utc_and_invalid_records_are_rejected():
    import merge_live_news as merger
    naive = {'url':'https://example.test/naive','title':'Naive timestamp','published_date':'2026-09-05T12:00:00'}
    rfc = {'url':'https://example.test/rfc','title':'RFC timestamp','published_date':'Sat, 05 Sep 2026 12:00:00 GMT'}
    invalid = {'url':'https://example.test/bad','title':'Bad timestamp','published_date':'not-a-date'}
    assert merger.normalize_article(naive)['published_date'] == '2026-09-05T12:00:00Z'
    assert merger.normalize_article(rfc)['published_date'] == '2026-09-05T12:00:00Z'
    assert merger.normalize_article(invalid) is None


def test_rss_parser_accepts_normal_feed_shape():
    import news_feed_db
    payload = b'''<?xml version="1.0"?><rss><channel><item><title>Fresh report</title><link>https://example.test/a</link><pubDate>Sat, 05 Sep 2026 12:00:00 GMT</pubDate><description>Summary</description></item></channel></rss>'''
    rows = news_feed_db.parse_feed(payload, 'test', {'name':'Example','type':'news','category':'test','url':'https://example.test/rss'})
    assert len(rows)==1 and rows[0]['url']=='https://example.test/a' and rows[0]['title']=='Fresh report' and rows[0]['source_name']=='Example'


def test_source_registry_preserves_explicit_categories():
    import news_feed_db
    registry = ROOT / 'data/sources.json'
    original = registry.read_bytes() if registry.exists() else None
    try:
        registry.write_text('{"feeds":[{"name":"Category Test","url":"https://example.test/rss","type":"news","category":"security"}]}', encoding='utf-8')
        sources = news_feed_db.load_sources()
        assert sources['category_test']['category'] == 'security'
    finally:
        if original is not None:
            registry.write_bytes(original)


def test_browser_qa_layer_is_installed_and_distinguishes_fetch_failure():
    text=(ROOT/'global_pulse_qa.js').read_text(encoding='utf-8'); assert 'LIVE DATA UNAVAILABLE' in text; assert 'gp.howToRead.v1' in text; assert 'gp-qa-contradiction' in text; assert 'aria-label' in text


def test_refresh_pipeline_requires_real_market_prices_and_manifest():
    text=(ROOT/'refresh_pipeline.py').read_text(encoding='utf-8'); assert 'market data contains no positive real prices' in text; assert 'refresh_manifest.json' in text; assert 'build_what_changed.py' in text


def test_refresh_projects_repaired_canonical_data_before_publishing_graph(monkeypatch):
    import refresh_pipeline as pipeline

    stages = []
    monkeypatch.setattr(pipeline, 'run', lambda label, *cmd: stages.append(cmd[1]))
    monkeypatch.setattr(pipeline, 'load', lambda name: {'rowsFetched': 1, 'exportedArticles': 1})
    monkeypatch.setattr(pipeline, 'verify_json', lambda *args, **kwargs: {})
    for name in ('verify_canonical_intelligence', 'verify_graph', 'verify_brain',
                 'verify_strategic_signals', 'verify_market'):
        monkeypatch.setattr(pipeline, name, lambda *args: None)
    monkeypatch.setattr(pipeline, 'write_refresh_manifest', lambda: None)
    monkeypatch.setattr(pipeline, 'REQUIRED_ARTIFACTS', ())
    assert pipeline.main() == 0
    expected = ['build_canonical_intelligence_v3.py', 'repair_strategic_targets.py',
                'repair_actor_target_roles.py', 'enrich_semantic_relationships.py',
                'trace_strategic_provenance.py', 'update_intelligence_web.py',
                'build_intelligence_graph.py', 'build_intelligence_brain.py',
                'validate_action_intelligence.py']
    assert [stage for stage in stages if stage in expected] == expected


def test_graph_projection_preserves_semantics_provenance_and_endpoint_limits(tmp_path, monkeypatch):
    import build_intelligence_graph as graph

    snapshot, output = tmp_path / 'snapshot.json', tmp_path / 'graph.json'
    nodes = [{'id': str(i), 'label': str(i), 'mentions': 200-i} for i in range(101)]
    nodes[-1]['mentions'] = 0
    evidence = [{'title': 'Explicit test source', 'url': 'https://example.test/source'}]
    edges = [dict(source='0', target='1', relationship=kind, eventIds=[event], evidence=evidence)
             for kind, event in [('trades_with', 'trade1'), ('sanctions', 'sanction'), ('trades_with', 'trade2')]]
    edges.append(dict(source='0', target='100', relationship='mentioned_with', evidence=evidence))
    snapshot.write_text(json.dumps({'intelligenceGraph': {'nodes': nodes, 'edges': edges}}), encoding='utf-8')
    monkeypatch.setattr(graph, 'SNAP', snapshot)
    monkeypatch.setattr(graph, 'OUT', output)
    graph.main()
    result = json.loads(output.read_text(encoding='utf-8'))
    assert len(result['nodes']) == 100
    assert len(result['edges']) == 2
    by_kind = {e['relationship']: e for e in result['edges']}
    assert by_kind['trades_with']['eventIds'] == ['trade1', 'trade2']
    assert by_kind['sanctions']['eventIds'] == ['sanction']
    ids = {node['id'] for node in result['nodes']}
    assert all(e['source'] in ids and e['target'] in ids for e in result['edges'])
    import validate_intelligence_graph as contract
    monkeypatch.setattr(contract, 'GRAPH', output)
    contract.main()
    result['edges'].append(dict(result['edges'][0]))
    output.write_text(json.dumps(result), encoding='utf-8')
    with pytest.raises(AssertionError, match='duplicate relationship claim'):
        contract.main()


def test_phase5_failover_preserves_existing_story_records():
    import source_failover
    existing=[{'url':'https://example.test/old','title':'Existing story','published_date':'2026-09-06T01:00:00Z'},{'url':'https://example.test/keep','title':'Another story','published_date':'2026-09-06T02:00:00Z'}]
    additions=[{'url':'https://example.test/new','title':'Fallback story','published_date':'2026-09-06T03:00:00Z'},{'url':'https://example.test/old','title':'Duplicate existing','published_date':'2026-09-06T04:00:00Z'}]
    merged=source_failover.merge_stories(existing,additions); assert len(merged)==3; assert [x['url'] for x in merged]==['https://example.test/old','https://example.test/keep','https://example.test/new']


def test_phase5_resilience_validator_is_wired_into_refresh_and_workflows():
    pipeline=(ROOT/'refresh_pipeline.py').read_text(encoding='utf-8'); workflow=(ROOT/'.github/workflows/update-snapshot.yml').read_text(encoding='utf-8'); diagnostics=(ROOT/'.github/workflows/data-resilience.yml').read_text(encoding='utf-8')
    assert 'validate_data_resilience.py' in pipeline and 'validate_data_resilience.py' in workflow and 'python validate_data_resilience.py' in diagnostics
    assert 'uses: actions/deploy-pages@v4' in workflow and 'uses: actions/deploy-pages@v4' not in diagnostics


def test_phase6_security_gate_and_hardening_cover_both_browser_surfaces():
    validator=(ROOT/'validate_security.py').read_text(encoding='utf-8'); hardener=(ROOT/'harden_site.py').read_text(encoding='utf-8')
    assert 'Content-Security-Policy' in validator and 'frame-ancestors' in validator and 'strict-origin-when-cross-origin' in validator
    assert 'Content-Security-Policy' in hardener and 'frame-ancestors' in hardener and 'strict-origin-when-cross-origin' in hardener
    for name in ('index.html','intelligence-web.html'):
        text=(ROOT/name).read_text(encoding='utf-8'); assert 'Content-Security-Policy' in text


def test_phase7_mobile_performance_layer_is_deferred_and_safe():
    index=(ROOT/'index.html').read_text(encoding='utf-8'); perf=(ROOT/'global_pulse_performance.js').read_text(encoding='utf-8'); qa=(ROOT/'global_pulse_qa.js').read_text(encoding='utf-8')
    assert 'global_pulse_performance.js' in index
    assert 'class="gp-intelweb-frame"' in index and 'loading="lazy"' in index
    assert 'loading="eager"' not in index
    assert 'IntersectionObserver' in perf and 'requestIdleCallback' in perf and 'contentVisibility' in perf
    assert 'prefers-reduced-motion' in perf
    assert 'requestAnimationFrame' in qa and 'MutationObserver' in qa


def test_phase8_operational_health_gate_is_source_preserving():
    validator=(ROOT/'validate_operational_health.py').read_text(encoding='utf-8')
    assert 'sourceBackedOnly' in validator
    assert 'lastSuccessfulRefresh' in validator
    assert 'invalid map coordinates' in validator
    assert 'Brain relationship lacks evidence' in validator
    assert 'excessive duplicate story identities' in validator


def test_strategic_actor_attribution_requires_action_local_context():
    from intelligence_entity_extractor import extract_entities
    from build_canonical_intelligence_v3 import participant_roles

    def roles(text, event_type):
        found_list=extract_entities(text)
        found={str(x['id']):x for x in found_list}
        names={str(x['id']):str(x['canonical_name']) for x in found_list}
        matched=list(names)
        actors,targets,_=participant_roles(found,matched,names,event_type,text)
        return {names[x] for x in actors}, {names[x] for x in targets}

    actors,_=roles('The United States imposed sanctions on Iran.', 'sanction')
    assert 'United States' in actors

    actors,_=roles('China deployed military forces near Taiwan.', 'military_action')
    assert 'China' in actors

    actors,_=roles('The military deployed forces near the border.', 'military_action')
    assert 'United States' not in actors and 'China' not in actors

    actors,_=roles('Washington announced a policy change affecting trade.', 'trade_action')
    assert 'United States' not in actors

    actors,_=roles('Beijing announced a policy change affecting trade.', 'trade_action')
    assert 'China' not in actors


def test_strategic_institution_attribution_requires_country_context_and_schema_supports_commands():
    from intelligence_entity_extractor import extract_entities
    from intelligence_schema import ENTITY_TYPES

    pentagon=extract_entities('The Pentagon announced new military deployments.')
    assert 'U.S. Department of Defense' in {x['canonical_name'] for x in pentagon}

    generic=extract_entities('The defense department announced new military deployments.')
    assert 'U.S. Department of Defense' not in {x['canonical_name'] for x in generic}

    chinese=extract_entities('China said the Central Military Commission approved the deployment.')
    assert 'Chinese Central Military Commission' in {x['canonical_name'] for x in chinese}
    assert 'military_command' in ENTITY_TYPES


def test_live_collector_has_explicit_us_and_china_coverage_contracts():
    import news_feed_db
    sources=news_feed_db.load_sources()
    us=[s for s in sources.values() if 'united-states' in s.get('coverage',[])]
    china=[s for s in sources.values() if 'china' in s.get('coverage',[])]
    assert len(us)>=2
    assert len(china)>=2
    assert any(s.get('category')=='china-security' for s in china)
    assert any(s.get('category')=='china-economics' for s in china)


def test_source_health_validator_requires_strategic_coverage():
    text=(ROOT/'validate_source_health.py').read_text(encoding='utf-8')
    assert 'REQUIRED_COVERAGE' in text
    assert 'united-states' in text and 'china' in text
    assert 'MIN_COVERAGE_SOURCES' in text
    assert 'rowsFetched' in text
