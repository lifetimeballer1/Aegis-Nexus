#!/usr/bin/env python3
import json
from pathlib import Path

p=Path('data/event_resolution.json')
if not p.exists(): raise SystemExit('event resolution artifact missing')
d=json.loads(p.read_text(encoding='utf-8'))
if not isinstance(d.get('events'),list): raise SystemExit('events must be a list')
for e in d['events']:
    if not e.get('resolution_id'): raise SystemExit('missing resolution_id')
    if not isinstance(e.get('event_ids'),list): raise SystemExit('event_ids must be a list')
    if e.get('confidence') not in {'low','moderate','high'}: raise SystemExit('invalid confidence')
print(f"validated {len(d['events'])} resolved event groups")
