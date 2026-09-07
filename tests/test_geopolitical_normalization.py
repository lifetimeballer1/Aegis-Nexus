from intelligence_entity_extractor import extract_entities


def canonical_names(text):
    return {entity["canonical_name"] for entity in extract_entities(text)}


def test_country_demonyms_resolve_to_canonical_entities():
    cases = {
        "Japanese officials responded to the announcement.": "Japan",
        "Indian officials announced a new policy.": "India",
        "Brazilian officials met with counterparts.": "Brazil",
        "British officials issued a statement.": "United Kingdom",
        "French officials responded.": "France",
        "German officials responded.": "Germany",
        "Australian officials responded.": "Australia",
        "Canadian officials responded.": "Canada",
        "Turkish officials responded.": "Turkey",
        "Saudi officials responded.": "Saudi Arabia",
    }
    for text, canonical in cases.items():
        assert canonical in canonical_names(text), text


def test_korean_is_not_ambiguous_by_itself():
    names = canonical_names("Korean officials discussed the issue.")
    assert "South Korea" not in names
    assert "North Korea" not in names


def test_explicit_south_and_north_korea_demonyms_resolve():
    assert "South Korea" in canonical_names("South Korean officials announced a policy.")
    assert "North Korea" in canonical_names("North Korean officials announced a policy.")


def test_japanese_target_is_canonicalized_as_japan():
    names = canonical_names("China targets Japanese chemical imports in an anti-dumping move.")
    assert "China" in names
    assert "Japan" in names
    assert "Japanese" not in names
