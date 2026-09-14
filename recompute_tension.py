#!/usr/bin/env python3
"""Recompute Global Tension from the CURRENT snapshot stories (anti-fossil step).

Pipeline position (refresh_pipeline.py): AFTER all story-mutating steps
(news_feed_db, source_failover) and BEFORE build_historical_trends.py, so the
trends sampler records a tension derived from the stories it ships with.

Why this exists: snapshot tension rotted at 41 (~Sept 6 2026) because no
pipeline step recomputed it — stories/conflicts/updatedAt were rewritten in
place while tension/breakdownScores were carried forward verbatim, and the only
other writer (finalize_intelligence_health.recalibrate) is ratchet-only
(max(old, new): tension can never fall) and unwired. This step is a PURE
function of current stories: tension can BOTH rise and fall.

Scoring reuses update_snapshot_fast.normalized_score / driver_evidence /
climate_metrics / build_early_warning with the same bases, weights and boosts,
so the pipeline score model stays identical to score model v5. History
appending stays owned by build_historical_trends.py — this step only reads
history.json (in-memory) for the early-warning momentum window.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import update_snapshot_fast as fast

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SNAP = DATA / 'snapshot.json'
HIST = DATA / 'history.json'

WEIGHTS = {'Conflict activity': .22, 'Diplomatic strain': .15, 'Economic pressure': .16,
           'Market volatility': .10, 'Military posture': .25,
           'Climate & humanitarian pressure': .12}
# Bases mirror update_snapshot_fast.main (35 conflict/military, 32 diplomatic/
# economic/market, 25 climate); boosts mirror it too. Keep in sync.
BASES = {'Conflict activity': 35, 'Diplomatic strain': 32, 'Economic pressure': 32,
         'Market volatility': 32, 'Military posture': 35,
         'Climate & humanitarian pressure': 25}
BOOSTS = {'Conflict activity': (r'airstrike', r'missile', r'drone', r'troops', r'offensive', r'shelling', r'invasion'),
          'Diplomatic strain': (r'sanction', r'expulsion', r'ultimatum', r'diplomatic crisis'),
          'Economic pressure': (r'tariff', r'sanction', r'supply disruption', r'recession'),
          'Market volatility': (r'selloff', r'plunge', r'surge', r'volatility'),
          'Military posture': (r'airstrike', r'missile', r'drone', r'troops', r'offensive', r'shelling', r'invasion'),
          'Climate & humanitarian pressure': ()}


def recompute(snapshot, history):
    """Recompute tension fields in place from snapshot['stories']; returns snapshot."""
    stories = [s for s in snapshot.get('stories', []) if isinstance(s, dict)]
    breakdown = {name: fast.normalized_score(stories, rx, BASES[name], pool, BOOSTS[name])
                 for name, (rx, pool) in fast.DRIVER_DEFS.items()}
    evidence = {name: fast.driver_evidence(stories, rx, pool)
                for name, (rx, pool) in fast.DRIVER_DEFS.items()}
    climate = fast.climate_metrics(stories)
    tension = int(round(sum(breakdown[k] * WEIGHTS[k] for k in WEIGHTS)))
    old_tension = snapshot.get('tension')
    delta = (tension - old_tension) if isinstance(old_tension, (int, float)) \
        and snapshot.get('scoreVersion') == fast.SCORE_VERSION else 0
    hp = [p for p in history if isinstance(p, dict)
          and p.get('scoreVersion') == fast.SCORE_VERSION]
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    early = fast.build_early_warning(tension, breakdown,
                                     hp + [{'updatedAt': now, 'tension': tension,
                                            'delta': delta, 'scoreVersion': fast.SCORE_VERSION}])
    snapshot['tension'] = tension
    snapshot['tensionDelta'] = delta
    snapshot['breakdownScores'] = breakdown
    snapshot['driverSignals'] = evidence
    snapshot['climatePressure'] = climate
    snapshot['earlyWarning'] = early
    snapshot['scoreVersion'] = fast.SCORE_VERSION
    snapshot['tensionMethod'] = ('V5: six-driver weighted index recomputed from current '
                                  f'snapshot stories every refresh ({len(stories)} stories); '
                                  'rises and falls with signal share, no ratchet.')
    return snapshot


def main():
    snapshot = json.loads(SNAP.read_text(encoding='utf-8'))
    try:
        history = json.loads(HIST.read_text(encoding='utf-8'))
        if not isinstance(history, list):
            history = []
    except Exception:
        history = []
    recompute(snapshot, history)
    SNAP.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')
    print('TENSION RECOMPUTE:', snapshot['tension'],
          'delta', snapshot['tensionDelta'], snapshot['breakdownScores'])


if __name__ == '__main__':
    main()
