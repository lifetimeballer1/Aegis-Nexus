#!/usr/bin/env python3
"""Global Pulse canonical refresh pipeline with explicit resilience gates."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data'
REQUIRED_ARTIFACTS=('snapshot.json','history.json','sources.json','live_articles.json','canonical_intelligence.json','intelligence_graph.json','intelligence_brain.json','map_points.json','strategic_signals.json','source_health.json')
MANIFEST_ARTIFACTS=('snapshot.json','history.json','sources.json','live_articles.json','canonical_intelligence.json','intelligence_graph.json','intelligence_brain.json','map_points.json','strategic_signals.json','source_health.json')
def run(label,*cmd):
 print(f'\n=== {label} ===',flush=True);print('$',' '.join(cmd),flush=True);subprocess.run(cmd,cwd=ROOT,check=True);print(f'PASS: {label}',flush=True)
def load(name):
 p=DATA/name
 if not p.is_file() or p.stat().st_size==0:raise RuntimeError(f'missing/empty artifact: {name}')
 return json.loads(p.read_text(encoding='utf-8'))
def fresh(obj,field='updatedAt',max_age=900):
 stamp=obj.get(field)
 if not stamp:raise RuntimeError(f'artifact has no {field}')
 dt=datetime.fromisoformat(str(stamp).replace('Z','+00:00'));age=(datetime.now(timezone.utc)-dt).total_seconds()
 if age < -120 or age > max_age:raise RuntimeError(f'artifact timestamp invalid/stale: age={age:.0f}s')
def verify_json(name,*,min_list=None,fresh_required=True,max_age=900):
 d=load(name)
 if fresh_required and isinstance(d,dict):fresh(d,max_age=max_age)
 if min_list:
  key,minimum=min_list
  if not isinstance(d.get(key),list) or len(d[key])<minimum:raise RuntimeError(f'{name}: {key} has fewer than {minimum} entries')
 return d
def verify_market(snapshot):
 market=snapshot.get('marketData') or {};indicators=market.get('indicators') or []
 if market.get('noApiKey') is not True:raise RuntimeError('market data must remain keyless')
 if len(indicators)<20:raise RuntimeError(f'market indicators={len(indicators)} < 20')
 real=[x for x in indicators if isinstance(x,dict) and float(x.get('price') or 0)>0]
 if not real:raise RuntimeError('market data contains no positive real prices')
def verify_strategic_signals(signals):
 if signals.get('sourceBackedOnly') is not True:raise RuntimeError('strategic signals are not source-backed')
 coverage=signals.get('majorActorCoverage') or {}
 for actor in ('United States','China'):
  if coverage.get(actor) is not True:raise RuntimeError(f'strategic signal missing for {actor}')
 for signal in signals.get('signals') or []:
  if not signal.get('actor') or not signal.get('signal') or not signal.get('evidence'):raise RuntimeError('strategic signal missing evidence')
def verify_brain(brain):
 if brain.get('complete') is not True or brain.get('sourceBackedOnly') is not True or brain.get('consolidated') is not True:raise RuntimeError('intelligence brain completeness/source/consolidation gate failed')
 nodes=brain.get('nodes') or [];edges=brain.get('edges') or []
 if len(nodes)<10 or len(nodes)>35 or brain.get('maxNodes')!=35:raise RuntimeError(f'intelligence brain size gate failed: {len(nodes)} nodes')
 if len(edges)<5:raise RuntimeError('intelligence brain verification failed: too few relationships')
 stats=brain.get('stats') if isinstance(brain.get('stats'),dict) else {}
 if stats.get('marketIndicators',0)<20:raise RuntimeError('intelligence brain market layer missing')
 ids={str(n.get('id')) for n in nodes}
 for actor in ('United States','China'):
  node=next((n for n in nodes if n.get('label')==actor),None)
  if not node:raise RuntimeError(f'major strategic actor missing: {actor}')
  if not node.get('evidence'):raise RuntimeError(f'major strategic actor has no evidence: {actor}')
 for n in nodes:
  if not any(isinstance(x,dict) and (x.get('url') or x.get('source')) for x in (n.get('evidence') or [])):raise RuntimeError(f'unsourced brain node: {n.get("label")}')
  if n.get('kind') not in {'country','cartel','economic','conflict','chokepoint'} or not n.get('canonical'):raise RuntimeError(f'noncanonical brain node: {n.get("label")}')
 for e in edges:
  if str(e.get('source')) not in ids or str(e.get('target')) not in ids or not e.get('evidence'):raise RuntimeError('invalid or unevidenced brain relationship')
def verify_canonical_intelligence(document):
 from intelligence_schema import validate_document
 errors=validate_document(document)
 if errors:raise RuntimeError(f'canonical intelligence schema validation failed: {errors[:5]}')
 if not document.get('generated_at'):raise RuntimeError('canonical intelligence has no generated_at timestamp')
 fresh(document,field='generated_at',max_age=1800)
 if len(document.get('entities') or [])==0:raise RuntimeError('canonical intelligence contains no entities')
 if len(document.get('evidence') or [])==0:raise RuntimeError('canonical intelligence contains no evidence')
def verify_graph(graph):
 if not isinstance(graph,dict):raise RuntimeError('intelligence graph is not an object')
 nodes=graph.get('nodes') or [];edges=graph.get('edges') or []
 if len(nodes)<10:raise RuntimeError(f'intelligence graph has only {len(nodes)} nodes')
 if len(edges)<5:raise RuntimeError(f'intelligence graph has only {len(edges)} edges')
 stamp=graph.get('updatedAt')
 if not stamp:raise RuntimeError('intelligence graph has no updatedAt timestamp')
 ids={str(n.get('id')) for n in nodes}
 for e in edges:
  if str(e.get('source')) not in ids or str(e.get('target')) not in ids or not e.get('evidence'):raise RuntimeError('intelligence graph contains invalid or unevidenced edge')
 for actor in ('United States','China'):
  node=next((n for n in nodes if n.get('label')==actor),None)
  if not node or not node.get('evidence'):raise RuntimeError(f'intelligence graph missing evidence-backed {actor} node')
def write_refresh_manifest():
 artifacts={}
 for name in MANIFEST_ARTIFACTS:
  path=DATA/name
  if not path.is_file() or path.stat().st_size==0:raise RuntimeError(f'cannot manifest missing/empty {name}')
  artifacts[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size}
 manifest={'version':1,'generatedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'artifacts':artifacts}
 (DATA/'refresh_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f"PASS: refresh manifest artifacts={len(artifacts)}",flush=True)
def main():
 run('Refresh live intelligence sources',sys.executable,'news_feed_db.py','--once')
 live_status=load('live_status.json')
 if int(live_status.get('rowsFetched',0))<=0:raise RuntimeError('live intelligence refresh returned no fetched rows')
 if int(live_status.get('exportedArticles',0))<=0:raise RuntimeError('live intelligence refresh exported no articles')
 run('Build current source health telemetry',sys.executable,'build_source_health.py')
 run('Validate current source health and strategic coverage',sys.executable,'validate_source_health.py')
 run('Build current evidence-backed snapshot graph',sys.executable,'update_intelligence_web.py')
 run('Build canonical intelligence layer',sys.executable,'build_canonical_intelligence_v3.py')
 run('Enrich semantic actor-action-target relationships',sys.executable,'enrich_semantic_relationships.py')
 canonical=verify_json('canonical_intelligence.json',fresh_required=False);verify_canonical_intelligence(canonical)
 run('Publish current Intelligence Web graph',sys.executable,'build_intelligence_graph.py')
 graph=verify_json('intelligence_graph.json');verify_graph(graph)
 run('Build compact major-node Intelligence Brain',sys.executable,'build_intelligence_brain.py')
 run('Guarantee U.S. and China major-power hubs',sys.executable,'ensure_major_power_nodes.py')
 run('Ensure Brain group coverage',sys.executable,'ensure_brain_groups.py')
 run('Enrich U.S. and China action intelligence',sys.executable,'enrich_brain_actions.py')
 run('Validate U.S. and China action intelligence',sys.executable,'validate_action_intelligence.py')
 run('Strict Brain validation',sys.executable,'validate_intelligence_brain.py')
 brain=verify_json('intelligence_brain.json');verify_brain(brain)
 run('Build strategic signals',sys.executable,'build_strategic_signals.py')
 signals=verify_json('strategic_signals.json',fresh_required=False);verify_strategic_signals(signals)
 snapshot=load('snapshot.json');verify_market(snapshot)
 run('Build what changed',sys.executable,'build_what_changed.py')
 for name in REQUIRED_ARTIFACTS:
  if not (DATA/name).exists():raise RuntimeError(f'missing required artifact: {name}')
 write_refresh_manifest()
 run('Validate data resilience',sys.executable,'validate_data_resilience.py')
 run('Validate final refresh manifest',sys.executable,'validate_data_resilience.py','--require-manifest')
 print('\n=== STRATEGIC INTELLIGENCE GATE: PASSED ===',flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
