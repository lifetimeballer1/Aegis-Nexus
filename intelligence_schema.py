"""Canonical intelligence data model for Global Pulse."""
from __future__ import annotations
from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from typing import Any,Dict,List,Optional
SCHEMA_VERSION="2.1"
ENTITY_TYPES={"country","government","government_agency","military","intelligence","political_party","person","company","financial_institution","international_organization","armed_group","region","location","conflict","infrastructure","technology","other"}
EVENT_TYPES={"military_action","diplomatic_action","economic_action","political_action","trade_action","sanction","cyber_activity","technology_action","energy_action","conflict_event","protest","election","disaster","other"}
RELATIONSHIP_TYPES={"allied_with","opposes","cooperates_with","negotiates_with","trades_with","sanctions","sanctioned_by","military_action_against","economic_action_toward","technology_action_toward","energy_action_toward","cyber_action_against","political_action_toward","deploys_to","supplies","targets","controls","located_in","member_of","owns","invests_in","depends_on","affects","participates_in","associated_with","mentioned_with","other"}
def utc_now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
@dataclass
class Evidence:
 id:str;title:str;source:str;url:str="";published_at:str="";reliability:float=.5;excerpt:str=""
@dataclass
class Entity:
 id:str;canonical_name:str;entity_type:str;aliases:List[str]=field(default_factory=list);country:Optional[str]=None;region:Optional[str]=None;importance:float=0.;mention_count:int=0;evidence_ids:List[str]=field(default_factory=list)
@dataclass
class Event:
 id:str;event_type:str;title:str;timestamp:str="";location:Optional[str]=None;severity:float=0.;confidence:float=0.;entity_ids:List[str]=field(default_factory=list);evidence_ids:List[str]=field(default_factory=list);actor_ids:List[str]=field(default_factory=list);target_ids:List[str]=field(default_factory=list);location_ids:List[str]=field(default_factory=list);action:str="";strategic_relevance:float=0.;score:float=0.
@dataclass
class Relationship:
 source_entity_id:str;relationship_type:str;target_entity_id:str;confidence:float=0.;weight:float=0.;first_seen:str="";last_seen:str="";evidence_ids:List[str]=field(default_factory=list);event_ids:List[str]=field(default_factory=list);strength:float=0.
@dataclass
class Signal:
 id:str;signal_type:str;severity:float;confidence:float;entity_ids:List[str]=field(default_factory=list);event_ids:List[str]=field(default_factory=list);impact:str="";evidence_ids:List[str]=field(default_factory=list)
def validate_document(d:Dict[str,Any])->List[str]:
 e=[];E=d.get("entities",[]);V=d.get("events",[]);R=d.get("relationships",[]);X=d.get("evidence",[]);S=d.get("signals",[]);ei={x.get("id") for x in E};vi={x.get("id") for x in V};xi={x.get("id") for x in X}
 if d.get("schema_version")!=SCHEMA_VERSION:e.append(f"schema_version must be {SCHEMA_VERSION}")
 for x in E:
  if not x.get("id") or not x.get("canonical_name"):e.append("entity missing id or canonical_name")
  if x.get("entity_type") not in ENTITY_TYPES:e.append(f"invalid entity_type: {x.get('entity_type')}")
  if not set(x.get("evidence_ids",[]))<=xi:e.append(f"entity {x.get('id')} references missing evidence")
 for x in V:
  if not x.get("id") or not x.get("event_type"):e.append("event missing id or event_type")
  if x.get("event_type") not in EVENT_TYPES:e.append(f"invalid event_type: {x.get('event_type')}")
  for k,label,ids in (("entity_ids","entities",ei),("actor_ids","actors",ei),("target_ids","targets",ei),("location_ids","locations",ei),("evidence_ids","evidence",xi)):
   if not set(x.get(k,[]))<=ids:e.append(f"event {x.get('id')} references missing {label}")
 for x in R:
  if x.get("source_entity_id") not in ei:e.append("relationship references missing source entity")
  if x.get("target_entity_id") not in ei:e.append("relationship references missing target entity")
  if x.get("relationship_type") not in RELATIONSHIP_TYPES:e.append(f"invalid relationship_type: {x.get('relationship_type')}")
  if not set(x.get("event_ids",[]))<=vi:e.append("relationship references missing event")
  if not set(x.get("evidence_ids",[]))<=xi:e.append("relationship references missing evidence")
 for x in S:
  if not x.get("id") or not x.get("signal_type"):e.append("signal missing id or signal_type")
  if not set(x.get("entity_ids",[]))<=ei:e.append(f"signal {x.get('id')} references missing entity")
  if not set(x.get("event_ids",[]))<=vi:e.append(f"signal {x.get('id')} references missing event")
 return e
def empty_document():return {"schema_version":SCHEMA_VERSION,"generated_at":utc_now(),"entities":[],"events":[],"relationships":[],"evidence":[],"signals":[],"metadata":{"model":"canonical-intelligence","source_backed_only":True}}
def dataclass_to_dict(v):return asdict(v)
