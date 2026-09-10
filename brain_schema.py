#!/usr/bin/env python3
"""Brain story/gap schema: deterministic fusion contracts.

Stories are canonical-event clusters. Gaps are evidence-backed missing pieces
with a lifecycle (open -> narrowing -> closed). Nothing here is generated:
every story and gap must cite the canonical evidence it came from.
"""
from __future__ import annotations

STORY_SCHEMA_VERSION = 1

SEVERITIES = ('critical', 'high', 'medium', 'low')
CONFIDENCES = ('high', 'moderate', 'limited', 'unverified')
STORY_STATUSES = ('active', 'narrowing', 'dormant', 'resolved')
GAP_TYPES = (
    'no_target',
    'single_source',
    'no_primary',
    'no_geo',
    'stale',
    'contradiction',
    'unresolved_duplicate',
    'no_assessment',
)
GAP_STATES = ('open', 'narrowing', 'closed')
SLOT_NAMES = ('actor', 'target', 'geo', 'time', 'outcome', 'corroboration', 'assessment')

STORY_REQUIRED = (
    'id', 'title', 'kind', 'severity', 'confidence', 'status', 'firstSeen',
    'lastUpdated', 'completeness', 'slots', 'evidence',
)
GAP_REQUIRED = (
    'id', 'storyId', 'type', 'severity', 'state', 'openedAt', 'updatedAt', 'evidenceNeeded',
)


def _is_iso(value):
    text = str(value or '')
    return len(text) >= 10 and text[4] == '-' and text[7] == '-'


def validate_evidence(items, where, errors, *, require_source=False):
    if not isinstance(items, list) or not items:
        errors.append(f'{where}: evidence must be a non-empty list')
        return
    for i, ev in enumerate(items):
        if not isinstance(ev, dict):
            errors.append(f'{where}.evidence[{i}]: not an object')
            continue
        title = str(ev.get('title') or '').strip()
        url = str(ev.get('url') or '').strip()
        source = str(ev.get('source') or '').strip()
        if not title and not url:
            errors.append(f'{where}.evidence[{i}]: needs a title or url')
        if require_source and not (url or source):
            errors.append(f'{where}.evidence[{i}]: needs a url or source')


def validate_stories(doc):
    """Return a list of contract errors for data/brain_stories.json."""
    errors = []
    if not isinstance(doc, dict):
        return ['brain_stories: document is not an object']
    if doc.get('version') != STORY_SCHEMA_VERSION:
        errors.append(f'brain_stories.version must be {STORY_SCHEMA_VERSION}')
    if doc.get('sourceBackedOnly') is not True:
        errors.append('brain_stories.sourceBackedOnly must be true')
    if not _is_iso(doc.get('updatedAt')):
        errors.append('brain_stories.updatedAt must be an ISO timestamp')
    stories = doc.get('stories')
    gaps = doc.get('gaps')
    if not isinstance(stories, list):
        errors.append('brain_stories.stories must be a list')
        stories = []
    if not isinstance(gaps, list):
        errors.append('brain_stories.gaps must be a list')
        gaps = []
    stats = doc.get('stats') if isinstance(doc.get('stats'), dict) else {}
    if stats.get('stories') != len(stories):
        errors.append('brain_stories.stats.stories must equal len(stories)')
    story_ids = set()
    for i, story in enumerate(stories):
        where = f'stories[{i}]'
        if not isinstance(story, dict):
            errors.append(f'{where}: not an object')
            continue
        for key in STORY_REQUIRED:
            if key not in story:
                errors.append(f'{where}: missing {key}')
        sid = str(story.get('id') or '').strip()
        if not sid:
            errors.append(f'{where}: empty id')
        elif sid in story_ids:
            errors.append(f'{where}: duplicate story id {sid}')
        story_ids.add(sid)
        if story.get('severity') not in SEVERITIES:
            errors.append(f'{where}: invalid severity {story.get("severity")!r}')
        if story.get('confidence') not in CONFIDENCES:
            errors.append(f'{where}: invalid confidence {story.get("confidence")!r}')
        if story.get('status') not in STORY_STATUSES:
            errors.append(f'{where}: invalid status {story.get("status")!r}')
        if not _is_iso(story.get('firstSeen')) or not _is_iso(story.get('lastUpdated')):
            errors.append(f'{where}: firstSeen/lastUpdated must be ISO timestamps')
        completeness = story.get('completeness')
        if not isinstance(completeness, (int, float)) or not (0.0 <= float(completeness) <= 1.0):
            errors.append(f'{where}: completeness must be a number in [0,1]')
        slots = story.get('slots')
        if not isinstance(slots, dict) or any(name not in slots for name in SLOT_NAMES):
            errors.append(f'{where}: slots must define {", ".join(SLOT_NAMES)}')
        elif any(not isinstance(slots.get(name), bool) for name in SLOT_NAMES):
            errors.append(f'{where}: slot values must be booleans')
        validate_evidence(story.get('evidence'), where, errors, require_source=True)
    valid_story_ids = story_ids
    gap_ids = set()
    gap_counts = {'open': 0, 'narrowing': 0, 'closed': 0}
    for i, gap in enumerate(gaps):
        where = f'gaps[{i}]'
        if not isinstance(gap, dict):
            errors.append(f'{where}: not an object')
            continue
        for key in GAP_REQUIRED:
            if key not in gap:
                errors.append(f'{where}: missing {key}')
        gid = str(gap.get('id') or '').strip()
        if not gid:
            errors.append(f'{where}: empty id')
        elif gid in gap_ids:
            errors.append(f'{where}: duplicate gap id {gid}')
        gap_ids.add(gid)
        if str(gap.get('storyId') or '') not in valid_story_ids:
            errors.append(f'{where}: storyId {gap.get("storyId")!r} does not match a story')
        if gap.get('type') not in GAP_TYPES:
            errors.append(f'{where}: invalid gap type {gap.get("type")!r}')
        if gap.get('state') not in GAP_STATES:
            errors.append(f'{where}: invalid gap state {gap.get("state")!r}')
        else:
            gap_counts[gap['state']] += 1
        if gap.get('severity') not in SEVERITIES:
            errors.append(f'{where}: invalid severity {gap.get("severity")!r}')
        if not _is_iso(gap.get('openedAt')) or not _is_iso(gap.get('updatedAt')):
            errors.append(f'{where}: openedAt/updatedAt must be ISO timestamps')
        if gap.get('state') == 'closed' and not _is_iso(gap.get('resolvedAt')):
            errors.append(f'{where}: closed gaps need resolvedAt')
        if gap.get('state') == 'closed':
            validate_evidence(gap.get('closingEvidence'), where, errors)
    for state, count in gap_counts.items():
        if stats.get(state) != count:
            errors.append(f'brain_stories.stats.{state} must equal {count}')
    if stats.get('withGaps') != sum(1 for s in stories if s.get('gapIds')):
        errors.append('brain_stories.stats.withGaps must equal stories having gaps')
    return errors


def validate_gap_history(doc):
    """Return a list of contract errors for data/brain_gap_history.json."""
    errors = []
    if not isinstance(doc, dict):
        return ['brain_gap_history: document is not an object']
    if doc.get('version') != STORY_SCHEMA_VERSION:
        errors.append(f'brain_gap_history.version must be {STORY_SCHEMA_VERSION}')
    if not _is_iso(doc.get('updatedAt')):
        errors.append('brain_gap_history.updatedAt must be an ISO timestamp')
    cycles = doc.get('cycles')
    gaps = doc.get('gaps')
    if not isinstance(cycles, list) or not cycles:
        errors.append('brain_gap_history.cycles must be a non-empty list')
        cycles = []
    if not isinstance(gaps, dict):
        errors.append('brain_gap_history.gaps must be an object keyed by gap id')
        gaps = {}
    for i, cycle in enumerate(cycles[-40:]):
        if not isinstance(cycle, dict) or not _is_iso(cycle.get('at')):
            errors.append(f'cycles[{i}]: needs ISO at timestamp')
    for gid, entry in gaps.items():
        if not isinstance(entry, dict):
            errors.append(f'gaps[{gid}]: not an object')
            continue
        if entry.get('state') not in GAP_STATES:
            errors.append(f'gaps[{gid}]: invalid state')
        if entry.get('type') not in GAP_TYPES:
            errors.append(f'gaps[{gid}]: invalid type')
        if not _is_iso(entry.get('openedAt')):
            errors.append(f'gaps[{gid}]: openedAt must be ISO')
        if entry.get('state') == 'closed' and not _is_iso(entry.get('resolvedAt')):
            errors.append(f'gaps[{gid}]: closed gap needs resolvedAt')
        history = entry.get('history')
        if not isinstance(history, list) or not history:
            errors.append(f'gaps[{gid}]: history must be a non-empty list')
    return errors
