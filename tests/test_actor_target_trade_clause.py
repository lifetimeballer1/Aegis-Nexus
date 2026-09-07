from build_canonical_intelligence_v3 import participant_roles
from intelligence_entity_extractor import extract_entities


def test_china_targets_japanese_trade_target():
    text = "China Targets Japanese Chemical Imports in Anti-Dumping Move."
    found_list = extract_entities(text)
    found = {str(x['id']): x for x in found_list}
    names = {str(x['id']): str(x['canonical_name']) for x in found_list}
    actors, targets, _ = participant_roles(found, list(names), names, 'trade_action', text)
    assert 'China' in {names[x] for x in actors}
    assert 'Japan' in {names[x] for x in targets}
