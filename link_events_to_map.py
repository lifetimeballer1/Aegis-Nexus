#!/usr/bin/env python3
"""Link geospatial markers to likely live-event clusters without changing map coordinates."""
from __future__ import annotations
import json,re
from pathlib import Path
DATA=Path(__file__).resolve().parent/'data'
STOP=set('the a an and or of to in on for from with by as at is are was were has have had this that report reports reported says said after before over into near amid during its their his her'.split())
def tokens(s):return {x for x in re.findall(r'[a-z0-9]{4,}',str(s or '').lower()) if x not in STOP}
def score(a,b):
 aa=tokens(a);bb=tokens(b);return len(aa&bb)/max(1,len(aa|bb))
def main():
 snap=json.loads((DATA/'snapshot.json').read_text(encoding='utf-8'));events=json.loads((DATA/'live_events.json').read_text(encoding='utf-8'));es=[e for e in events.get('events',[]) if isinstance(e,dict)];links=[];review=0
 for idx,m in enumerate(snap.get('markers',[])):
  if not isinstance(m,dict):continue
  text=' '.join(str(m.get(k) or '') for k in ('title','detail','description','conflictName'));best=None;best_score=0
  for e in es:
   s=score(text,e.get('title'))
   if s>best_score:best,best_score=e,s
  if best and best_score>=.32:
   links.append({'markerIndex':idx,'lat':m.get('lat'),'lng':m.get('lng'),'eventId':best.get('id'),'eventTitle':best.get('title'),'confidence':'candidate' if best_score<.5 else 'strong-candidate','matchScore':round(best_score,3)})
   if best_score<.5:review+=1
 out={'version':1,'updatedAt':events.get('updatedAt'),'markerCount':len(snap.get('markers',[])),'linkedMarkers':len(links),'reviewCandidates':review,'method':'Token-overlap candidate linking between marker text and live-event titles. Coordinates are read-only and never inferred or moved.','links':links}
 (DATA/'map_event_links.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print('MAP EVENT LINKS:',len(links),'linked /',review,'review candidates')
if __name__=='__main__':main()
