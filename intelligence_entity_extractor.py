"""Reusable, dependency-free entity extraction and canonicalization utilities."""
from __future__ import annotations
import hashlib
import re
from typing import Iterable

CANONICAL_ALIASES = {
    "United States": ("country", {"united states", "u.s.", "u.s", "usa", "american", "washington"}),
    "China": ("country", {"china", "chinese", "beijing"}),
    "Russia": ("country", {"russia", "russian", "moscow"}),
    "Ukraine": ("country", {"ukraine", "ukrainian", "kyiv"}),
    "Taiwan": ("country", {"taiwan", "taiwanese", "taipei"}),
    "Iran": ("country", {"iran", "iranian", "tehran"}),
    "Israel": ("country", {"israel", "israeli", "jerusalem"}),
    "NATO": ("international_organization", {"nato"}),
    "European Union": ("international_organization", {"european union", "eu"}),
    "United Nations": ("international_organization", {"united nations", "u.n."}),
    "People's Liberation Army": ("military", {"people's liberation army", "pla", "pla forces", "pla navy", "pla air force", "pla rocket force"}),
    "Communist Party of China": ("political_party", {"communist party of china", "ccp", "cpc", "chinese communist party"}),
    "Chinese State Council": ("government", {"chinese state council", "china's state council", "prc state council"}),
    "Chinese Central Military Commission": ("military_command", {"central military commission", "chinese central military commission", "china's central military commission"}),
    "Chinese Ministry of Foreign Affairs": ("government_agency", {"chinese ministry of foreign affairs", "chinese foreign ministry", "china's ministry of foreign affairs", "china foreign ministry"}),
    "Chinese Ministry of Commerce": ("government_agency", {"chinese ministry of commerce", "chinese commerce ministry", "china's ministry of commerce", "china commerce ministry"}),
    "U.S. Department of Defense": ("government_agency", {"department of defense", "defense department", "pentagon"}),
    "U.S. Department of State": ("government_agency", {"department of state", "state department"}),
    "U.S. Treasury": ("government_agency", {"u.s. treasury", "treasury department"}),
    "U.S. Congress": ("government", {"u.s. congress", "congress", "house of representatives", "senate"}),
    "White House": ("government", {"white house"}),
    "Federal Reserve": ("financial_institution", {"federal reserve", "fed"}),
    "JPMorgan": ("financial_institution", {"jpmorgan", "jpmorgan chase"}),
}

# Generic phrases are promoted only when nearby Chinese context makes the
# institutional attribution defensible. This avoids mapping every mention of
# "the military" or "the foreign ministry" to China.
CONTEXT_RULES = (
    ("People's Liberation Army", "military", re.compile(r"\b(?:china(?:'s)?|chinese|beijing)\b[^.!?]{0,90}\b(?:military|armed forces|army|navy|air force|rocket force)\b|\b(?:military|armed forces|army|navy|air force|rocket force)\b[^.!?]{0,90}\b(?:china(?:'s)?|chinese|beijing)\b", re.I)),
    ("Communist Party of China", "political_party", re.compile(r"\b(?:china(?:'s)?|chinese|beijing)\b[^.!?]{0,90}\b(?:communist party|party leadership|party officials|party committee)\b|\b(?:communist party|party leadership|party officials|party committee)\b[^.!?]{0,90}\b(?:china(?:'s)?|chinese|beijing)\b", re.I)),
    ("Chinese State Council", "government", re.compile(r"\b(?:china(?:'s)?|chinese|beijing)\b[^.!?]{0,90}\bstate council\b|\bstate council\b[^.!?]{0,90}\b(?:china(?:'s)?|chinese|beijing)\b", re.I)),
    ("Chinese Ministry of Foreign Affairs", "government_agency", re.compile(r"\b(?:china(?:'s)?|chinese|beijing)\b[^.!?]{0,90}\b(?:foreign ministry|foreign minister|foreign ministry officials|diplomatic ministry)\b|\b(?:foreign ministry|foreign minister|foreign ministry officials|diplomatic ministry)\b[^.!?]{0,90}\b(?:china(?:'s)?|chinese|beijing)\b", re.I)),
    ("Chinese Ministry of Commerce", "government_agency", re.compile(r"\b(?:china(?:'s)?|chinese|beijing)\b[^.!?]{0,90}\b(?:commerce ministry|ministry of commerce|trade ministry)\b|\b(?:commerce ministry|ministry of commerce|trade ministry)\b[^.!?]{0,90}\b(?:china(?:'s)?|chinese|beijing)\b", re.I)),
)

DISCOVERY_RULES = (
    ("government_agency", re.compile(r"\b(?:Department|Ministry|Agency|Office)\s+(?:of\s+)?(?:[A-Z][\w'’-]+\s*){1,5}")),
    ("military", re.compile(r"\b(?:[A-Z][\w'’-]+\s+){1,5}(?:Army|Navy|Air Force|Armed Forces|Defense Forces|Corps)\b")),
    ("company", re.compile(r"\b(?:[A-Z][\w&'.-]+\s+){1,5}(?:Inc\.?|Corp\.?|Corporation|Ltd\.?|LLC|Holdings|Group)\b")),
    ("financial_institution", re.compile(r"\b(?:[A-Z][\w&'.-]+\s+){1,5}(?:Bank|Fund|Capital|Finance)\b")),
    ("international_organization", re.compile(r"\b(?:[A-Z][\w'’-]+\s+){1,5}(?:Organization|Organisation|Alliance|Union)\b")),
)
PERSON_RULE = re.compile(r"\b(?:President|Vice President|Prime Minister|Chancellor|Secretary|Minister|Senator|Representative|General|Admiral|Ambassador|Director|Chairman|Chairwoman|CEO|CFO)\s+(?:[A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+){0,3})")
LOCATION_RULE = re.compile(r"\b(?:in|near|at|from|to|toward|around|across|inside|outside|off)\s+([A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+){0,2}\s+(?:City|State|Province|Region|District|County|Island|Islands|Sea|Strait|Gulf|Bay|River|Lake|Peninsula|Valley|Mount|Mountain))\b|\b([A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+){0,2}\s+(?:City|State|Province|Region|District|County|Island|Islands|Sea|Strait|Gulf|Bay|River|Lake|Peninsula|Valley|Mount|Mountain))\b")

def entity_id(canonical_name: str, entity_type: str) -> str:
    digest = hashlib.sha256(f"{entity_type}|{canonical_name.lower()}".encode()).hexdigest()[:16]
    return f"ent-{digest}"

def normalize_known(text: str) -> list[dict]:
    lowered = text.lower(); found=[]
    for canonical,(entity_type,aliases) in CANONICAL_ALIASES.items():
        matched=sorted({a for a in aliases if re.search(r"(?<![a-z])"+re.escape(a)+r"(?![a-z])", lowered)})
        if matched: found.append({"id":entity_id(canonical,entity_type),"canonical_name":canonical,"entity_type":entity_type,"aliases":matched})
    return found

def resolve_context_entities(text: str) -> list[dict]:
    found=[]
    for canonical, entity_type, rule in CONTEXT_RULES:
        if rule.search(text):
            found.append({"id":entity_id(canonical,entity_type),"canonical_name":canonical,"entity_type":entity_type,"aliases":["context_resolved"],"context_resolved":True})
    return found

def discover_named_entities(text: str, excluded_names: Iterable[str] = ()) -> list[dict]:
    excluded={n.casefold() for n in excluded_names};known={n.casefold() for n in CANONICAL_ALIASES};output={}
    for entity_type,rule in DISCOVERY_RULES:
        for match in rule.finditer(text):
            candidate=" ".join(match.group(0).split()).strip(" ,.;:()[]");key=(entity_type,candidate.casefold())
            if len(candidate)>=4 and candidate.casefold() not in excluded and candidate.casefold() not in known: output[key]={"id":entity_id(candidate,entity_type),"canonical_name":candidate,"entity_type":entity_type,"aliases":[],"discovered":True}
    for match in PERSON_RULE.finditer(text):
        candidate=" ".join(match.group(0).split()).strip(" ,.;:()[]");key=("person",candidate.casefold())
        if len(candidate)>=6 and candidate.casefold() not in excluded and candidate.casefold() not in known: output[key]={"id":entity_id(candidate,"person"),"canonical_name":candidate,"entity_type":"person","aliases":[],"discovered":True}
    for match in LOCATION_RULE.finditer(text):
        candidate=next((g for g in match.groups() if g),"");candidate=" ".join(candidate.split()).strip(" ,.;:()[]")
        if len(candidate)>=4 and candidate.casefold() not in excluded and candidate.casefold() not in known: output.setdefault(("location",candidate.casefold()),{"id":entity_id(candidate,"location"),"canonical_name":candidate,"entity_type":"location","aliases":[],"discovered":True})
    return list(output.values())

def extract_entities(text: str) -> list[dict]:
    known=normalize_known(text)
    resolved=resolve_context_entities(text)
    existing={e["canonical_name"] for e in known}
    known.extend(e for e in resolved if e["canonical_name"] not in existing)
    return known+discover_named_entities(text,excluded_names=(e["canonical_name"] for e in known))
