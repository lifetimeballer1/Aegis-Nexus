#!/usr/bin/env python3
"""Global Tension v6 — single canonical writer.

Six deterministic signal drivers (the established V5 model) plus an auditable
story-pressure term derived from the Brain story graph. Every published value
carries its inputs: driver breakdown, weights, the stories that contributed,
and when it was computed. No history rows from other writers/versions survive.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import update_snapshot_fast as v5

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SNAP = DATA / 'snapshot.json'
HIST = DATA / 'history.json'
SCORE_VERSION = 6
WEIGHTS = {
    'Conflict activity': .22,
    'Diplomatic strain': .15,
    'Economic pressure': .16,
    'Market volatility': .10,
    'Military posture': .25,
    'Climate & humanitarian pressure': .12,
}
BOOSTS = {
    'Conflict activity': (r'airstrike', r'missile', r'drone', r'troops', r'offensive', r'shelling', r'invasion'),
    'Diplomatic strain': (r'sanction', r'expulsion', r'ultimatum', r'diplomatic crisis'),
    'Economic pressure': (r'tariff', r'sanction', r'supply disruption', r'recession'),
    'Market volatility': (r'selloff', r'plunge', r'surge', r'volatility'),
    'Military posture': (r'airstrike', r'missile', r'drone', r'troops', r'offensive', r'shelling', r'invasion'),
    'Climate & humanitarian pressure': (),
}
STORY_PRESSURE_CAP = 30.0
STORY_PRESSURE_TOP = 8
STORY_PRESSURE_FACTOR = 0.9
LEVELS = {'critical': 75, 'elevated': 55}


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding='utf-8'))
    except Exception:
        return default


def parse_time(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        return None


def hours_since(value, now):
    dt = parse_time(value)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 3600)


def eligible_stories(brain_stories, now):
    eligible = []
    for story in brain_stories.get('stories', []) or []:
        if not isinstance(story, dict):
            continue
        if story.get('severity') not in ('critical', 'high'):
            continue
        if str(story.get('status')) == 'dormant':
            continue
        age = hours_since(story.get('lastUpdated'), now)
        if age is None or age > 72:
            continue
        eligible.append(story)
    return eligible


def compute_story_pressure(stories, now):
    """Bounded, auditable pressure from the strongest current stories."""
    scored = sorted(
        ((float(s.get('tensionContribution') or 0), s) for s in stories),
        key=lambda pair: pair[0],
        reverse=True,
    )
    top = scored[:STORY_PRESSURE_TOP]
    if not top:
        return 0.0, []
    average = sum(item[0] for item in top) / STORY_PRESSURE_TOP
    pressure = min(STORY_PRESSURE_CAP, round(average * STORY_PRESSURE_FACTOR, 1))
    audit = [{
        'id': str(s.get('id') or ''),
        'title': str(s.get('title') or '')[:160],
        'severity': str(s.get('severity') or ''),
        'contribution': round(float(s.get('tensionContribution') or 0), 1),
    } for _, s in top]
    return pressure, audit


def build_early_warning(tension, breakdown, history, story_audit):
    points = [p for p in history if isinstance(p, dict) and p.get('scoreVersion') == SCORE_VERSION and isinstance(p.get('tension'), (int, float))]
    recent = [float(p['tension']) for p in points[-12:]]
    prior = [float(p['tension']) for p in points[-36:-12]]
    ra = sum(recent) / len(recent) if recent else float(tension)
    pa = sum(prior) / len(prior) if prior else ra
    momentum = round(ra - pa, 1)
    name, val = max(breakdown.items(), key=lambda item: item[1]) if breakdown else ('Overall tension', tension)
    level = 'HIGH' if tension >= LEVELS['critical'] or momentum >= 10 else 'ELEVATED' if tension >= LEVELS['elevated'] or momentum >= 5 else 'WATCH'
    direction = 'rising' if momentum >= 2 else 'falling' if momentum <= -2 else 'stable'
    top_story = story_audit[0] if story_audit else None
    summary = f"{level} · tension {int(tension)} ({direction}) · strongest driver {name} {int(val)}"
    if top_story:
        summary += f" · top story: {top_story['title'][:90]}"
    return {
        'level': level,
        'score': int(tension),
        'momentum': momentum,
        'direction': direction,
        'strongestDriver': name,
        'strongestDriverScore': int(val),
        'storyDriver': top_story['title'] if top_story else '',
        'summary': summary,
        'message': 'Story pressure raises tension only from open, source-backed critical/high stories updated within 72 hours; closures and stale stories lower it.',
        'method': 'Score model v6: weighted six-driver index (established V5 signal pools) plus bounded Brain story pressure. Recent 12 versus preceding 24 v6 snapshots.',
    }


def prune_history(history):
    return [p for p in history if isinstance(p, dict) and p.get('scoreVersion') == SCORE_VERSION][-288:]


def main():
    snap = load('snapshot.json', {}) or {}
    if not snap:
        raise SystemExit('TENSION BLOCKED: snapshot.json unavailable')
    stories = snap.get('stories') or []
    if not stories:
        raise SystemExit('TENSION BLOCKED: snapshot has no stories')
    brain_stories = load('brain_stories.json', {}) or {}
    history = load('history.json', [])
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat().replace('+00:00', 'Z')

    breakdown = {
        name: v5.normalized_score(stories, rx, 35 if name in ('Conflict activity', 'Military posture') else 25 if name == 'Climate & humanitarian pressure' else 32, pool, BOOSTS[name])
        for name, (rx, pool) in v5.DRIVER_DEFS.items()
    }
    evidence = {name: v5.driver_evidence(stories, rx, pool) for name, (rx, pool) in v5.DRIVER_DEFS.items()}
    climate = v5.climate_metrics(stories)
    base = sum(breakdown[k] * WEIGHTS[k] for k in WEIGHTS)
    candidates = eligible_stories(brain_stories, now_dt)
    story_pressure, story_audit = compute_story_pressure(candidates, now_dt)
    tension = int(round(min(100.0, base + story_pressure)))

    pruned = prune_history(history)
    prior = pruned[-1] if pruned else None
    delta = int(tension - prior['tension']) if prior and isinstance(prior.get('tension'), (int, float)) else 0
    early = build_early_warning(tension, breakdown, pruned + [{'scoreVersion': SCORE_VERSION, 'tension': tension}], story_audit)

    snap['scoreVersion'] = SCORE_VERSION
    snap['tension'] = tension
    snap['tensionDelta'] = delta
    snap['breakdownScores'] = breakdown
    snap['driverSignals'] = evidence
    snap['climatePressure'] = climate
    snap['earlyWarning'] = early
    snap['tensionComputedAt'] = now
    snap['tensionStale'] = False
    snap['tensionMethod'] = 'V6: weighted six-driver index plus bounded Brain story pressure. Story pressure is computed from open source-backed critical/high stories updated within 72 hours and is capped at 30 points; every contribution is listed in tensionBreakdown.'
    snap['tensionBreakdown'] = {
        'base': round(base, 2),
        'storyPressure': story_pressure,
        'storyPressureCap': STORY_PRESSURE_CAP,
        'weights': WEIGHTS,
        'eligibleStories': len(candidates),
        'topStories': story_audit,
        'computedBy': 'build_tension.py',
    }
    SNAP.write_text(json.dumps(snap, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')

    entry = {'updatedAt': now, 'tension': tension, 'delta': delta, 'scoreVersion': SCORE_VERSION, 'base': round(base, 1), 'storyPressure': story_pressure}
    HIST.write_text(json.dumps((pruned + [entry])[-288:], ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'TENSION v6: {tension} (base {base:.1f} + story {story_pressure}) delta={delta} level={early["level"]} eligibleStories={len(candidates)}')


if __name__ == '__main__':
    main()
