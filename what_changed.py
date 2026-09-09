#!/usr/bin/env python3
"""Build a compact, evidence-first last-24h change feed from the current snapshot."""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

p=Path('snapshot.json')
d=json.loads(p.read_text(encoding='utf-8'))
now=datetime.now(timezone.utc)
cutoff=now-timedelta(hours=24)


def parse_dt(v):
    if not v: return None
    try:
        s=str(v).replace('Z','+00:00')
        dt=datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception: return None

changes=[]
for s in d.get('stories',[]):
    if not isinstance(s,dict): continue
    dt=parse_dt(s.get('published') or s.get('published_at') or s.get('timestamp') or s.get('date'))
    if dt and dt >= cutoff:
        title=str(s.get('title') or s.get('headline') or '').strip()
        if title:
            changes.append({'type':'NEWS','title':title,'source':s.get('source') or s.get('source_name'),'url':s.get('url'),'timestamp':dt.isoformat()})

# Keep the generated artifact bounded; the UI can render this without processing the full news corpus.
changes.sort(key=lambda x:x['timestamp'], reverse=True)
d['last_24h_changes']=changes[:80]
d['last_24h_generated_at']=now.isoformat()
p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8',newline='\n')
print(f'Generated {len(d["last_24h_changes"])} last-24h changes')
