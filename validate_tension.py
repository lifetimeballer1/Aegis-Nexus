#!/usr/bin/env python3
"""Fail-closed validation for the Global Tension v6 contract (B26)."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'


def main() -> int:
    errors = []
    try:
        snap = json.loads((DATA / 'snapshot.json').read_text(encoding='utf-8'))
    except Exception as exc:
        print(f'TENSION VALIDATION FAILED: snapshot unavailable: {exc}')
        return 1
    tension = snap.get('tension')
    if not isinstance(tension, (int, float)) or not (0 <= float(tension) <= 100):
        errors.append(f'tension out of range: {tension!r}')
    if snap.get('scoreVersion') != 6:
        errors.append(f'scoreVersion must be 6, found {snap.get("scoreVersion")!r}')
    if not snap.get('tensionComputedAt'):
        errors.append('tensionComputedAt missing')
    if snap.get('tensionStale') is not False:
        errors.append('tensionStale must be false after the canonical writer runs')
    if not snap.get('tensionMethod'):
        errors.append('tensionMethod missing')
    breakdown = snap.get('tensionBreakdown') or {}
    base = breakdown.get('base')
    pressure = breakdown.get('storyPressure')
    if not isinstance(base, (int, float)) or not isinstance(pressure, (int, float)):
        errors.append('tensionBreakdown.base/storyPressure missing')
    else:
        if abs((float(base) + float(pressure)) - float(tension or 0)) > 1.0:
            errors.append(f'tension {tension} != base {base} + storyPressure {pressure}')
        if float(pressure) > float(breakdown.get('storyPressureCap') or 30) + 1e-6:
            errors.append('story pressure exceeds its documented cap')
    scores = snap.get('breakdownScores') or {}
    weights = breakdown.get('weights') or {}
    if not scores or not weights:
        errors.append('driver breakdown or weights missing')
    else:
        if set(scores) != set(weights):
            errors.append('driver names must match the published weights')
        if any(not (0 <= float(v) <= 100) for v in scores.values()):
            errors.append('driver scores out of range')
    early = snap.get('earlyWarning') or {}
    if early.get('level') not in ('HIGH', 'ELEVATED', 'WATCH'):
        errors.append(f'invalid early warning level: {early.get("level")!r}')
    if not early.get('summary'):
        errors.append('early warning summary missing')
    try:
        history = json.loads((DATA / 'history.json').read_text(encoding='utf-8'))
    except Exception as exc:
        errors.append(f'history unavailable: {exc}')
        history = []
    if not isinstance(history, list) or not history:
        errors.append('history empty')
    else:
        bad = [p for p in history if not isinstance(p, dict) or p.get('scoreVersion') != 6]
        if bad:
            errors.append(f'{len(bad)} history rows are not v6 (multiple writers detected)')
        last = history[-1]
        if last.get('tension') != tension:
            errors.append('history last tension does not match snapshot tension')
        stamp = last.get('updatedAt')
        computed = snap.get('tensionComputedAt')
        try:
            if datetime.fromisoformat(str(stamp).replace('Z', '+00:00')).timestamp() != datetime.fromisoformat(str(computed).replace('Z', '+00:00')).timestamp():
                errors.append('history timestamp does not match tensionComputedAt')
        except Exception:
            errors.append('history/snapshot timestamps unparsable')
    if errors:
        print('TENSION VALIDATION FAILED:')
        for error in errors:
            print(f'  - {error}')
        return 1
    print(f'TENSION VALIDATION PASSED: {tension} (base {base} + story {pressure}) level={early.get("level")}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
