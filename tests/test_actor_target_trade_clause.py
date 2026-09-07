from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from build_canonical_intelligence_v3 import participant_roles
from intelligence_entity_extractor import extract_entities
from repair_actor_target_roles import PATTERNS


def test_china_targets_japanese_trade_target():
    text = "China Targets Japanese Chemical Imports in Anti-Dumping Move."
    found_list = extract_entities(text)
    found = {str(x['id']): x for x in found_list}
    names = {str(x['id']): str(x['canonical_name']) for x in found_list}
    actors, targets, _ = participant_roles(found, list(names), names, 'trade_action', text)
    assert 'China' in {names[x] for x in actors}
    assert 'Japan' in {names[x] for x in targets}


def test_actor_target_repair_accepts_explicit_trade_target_clause():
    text = "China Targets Japanese Chemical Imports in Anti-Dumping Move."
    clauses = []
    for pattern in PATTERNS['trade_action']:
        clauses.extend(m.group(1) for m in re.finditer(pattern, text, re.I))
    assert any('Japanese Chemical Imports in Anti-Dumping Move' in clause for clause in clauses)

# Production-refresh trigger marker: keeps this regression on the canonical workflow path.
