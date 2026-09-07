#!/usr/bin/env python3
"""Evidence-only diagnostic for strategic actor events."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'
def article_text(a): return ' '.join(str(a.get(k) or '') for k in ('title','summary_snippet','summary','description','content')).strip()
def main():
    canonical=json.loads((DATA/'canonical_intelligence.json').read_text(encoding='utf-8'))
    live=json.loads((DATA/'live_articles.json').read_text(encoding='utf-8'))
    articles={str(a.get('url')):a for a in live.get('articles',[]) if isinstance(a,dict) and a.get('url')}
    evidence={str(e.get('id')):e for e in canonical.get('evidence',[]) if isinstance(e,dict)}
    entities={str(e.get('id')):e for e in canonical.get('entities',[]) if isinstance(e,dict)}
    print('=== STRATEGIC EVENT DIAGNOSTIC ===')
    for actor_name in ('China','United States'):
        ids={eid for eid,e in entities.items() if e.get('canonical_name')==actor_name}
        events=[e for e in canonical.get('events',[]) if ids & {str(x) for x in e.get('actor_ids',[])}]
        print(f'{actor_name}: events={len(events)}')
        for ev in events:
            names=lambda xs:[entities.get(str(x),{}).get('canonical_name',x) for x in xs]
            print(f"EVENT {ev.get('id')} type={ev.get('event_type')} actors={names(ev.get('actor_ids',[]))} targets={names(ev.get('target_ids',[]))}")
            for evid in ev.get('evidence_ids',[]):
                item=evidence.get(str(evid),{}); url=str(item.get('url') or ''); a=articles.get(url)
                txt=article_text(a) if a else ' '.join(str(item.get(k) or '') for k in ('title','excerpt'))
                print('  URL:',url)
                print('  EVIDENCE:',txt[:1600].replace('\n',' '))
    print('=== END STRATEGIC EVENT DIAGNOSTIC ===')
    return 0
if __name__=='__main__': raise SystemExit(main())
