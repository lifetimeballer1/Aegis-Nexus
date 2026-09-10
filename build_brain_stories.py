#!/usr/bin/env python3
"""Build the Brain story graph: canonical event clusters with evidence-backed
gaps and refresh-driven gap closure.

Deterministic and source-backed only: every story and gap cites canonical
records. Gap lifecycle (open -> narrowing -> closed) is derived by comparing
this refresh against the previously published story artifact. Nothing is
generated; missing pieces are stated, never invented.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from brain_schema import STORY_SCHEMA_VERSION, SLOT_NAMES

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
STORIES = DATA / 'brain_stories.json'
GAP_HISTORY = DATA / 'brain_gap_history.json'

SEVERITY_WEIGHT = {'critical': 1.0, 'high': 0.75, 'medium': 0.5, 'low': 0.25}
GRADE_CONFIDENCE = {'A': 'high', 'B': 'high', 'C': 'moderate', 'D': 'limited'}
BREAKING = re.compile(r'strike|attack|missile|drone|killed|shelling|airstrike|invasion|offensive|bomb|clash|escalat', re.I)
OPEN_SLOT = re.compile(r'[a-z0-9]{4,}')


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


def hours_ago(value):
    dt = parse_time(value)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)


def stable_id(prefix, *parts):
    digest = hashlib.sha1('|'.join(str(p) for p in parts).encode('utf-8')).hexdigest()[:10]
    return f'{prefix}-{digest}'


def tokens(text):
    return {t for t in OPEN_SLOT.findall(str(text or '').lower())}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def join_indexes():
    canonical = load('canonical_intelligence.json', {}) or {}
    entities = {str(e.get('id')): e for e in canonical.get('entities', []) if isinstance(e, dict) and e.get('id')}
    evidence = {str(e.get('id')): e for e in canonical.get('evidence', []) if isinstance(e, dict) and e.get('id')}
    events_by_url = {}
    canon_events = []
    for event in canonical.get('events', []):
        if not isinstance(event, dict):
            continue
        urls = []
        for eid in event.get('evidence_ids', []) or []:
            ev = evidence.get(str(eid))
            if ev and ev.get('url'):
                urls.append(str(ev['url']))
        event['_urls'] = urls
        canon_events.append(event)
        for url in urls:
            events_by_url.setdefault(url, []).append(event)
    event_intel = {str(e.get('eventId')): e for e in (load('event_intelligence.json', {}) or {}).get('events', []) if isinstance(e, dict)}
    source_ev = {str(e.get('eventId')): e for e in (load('source_evidence.json', {}) or {}).get('eventSourceEvidence', []) if isinstance(e, dict)}
    impacts = {str(e.get('eventId')): e for e in (load('intelligence_assessment.json', {}) or {}).get('eventImpacts', []) if isinstance(e, dict)}
    consistency = {str(e.get('eventId')): e for e in (load('event_consistency.json', {}) or {}).get('events', []) if isinstance(e, dict)}
    resolution = {}
    resolution_doc = load('event_resolution.json', {}) or {}
    res_groups = resolution_doc.get('events', []) if isinstance(resolution_doc.get('events'), list) else []
    for group in res_groups:
        if not isinstance(group, dict):
            continue
        for event_id in group.get('event_ids', []) or []:
            resolution[str(event_id)] = group
    claims = [c for c in (load('claims.json', {}) or {}).get('claims', []) if isinstance(c, dict)]
    claim_urls = []
    for claim in claims:
        urls = set()
        for item in claim.get('evidence', []) or []:
            if isinstance(item, dict) and item.get('url'):
                urls.add(str(item['url']))
        for item in claim.get('sources', []) or []:
            if isinstance(item, str) and item.startswith('http'):
                urls.add(item)
        claim['_urls'] = urls
        claim['_tokens'] = tokens(claim.get('claim'))
        claim_urls.append(claim)
    return {
        'entities': entities,
        'evidence': evidence,
        'events_by_url': events_by_url,
        'canon_events': canon_events,
        'event_intel': event_intel,
        'source_ev': source_ev,
        'impacts': impacts,
        'consistency': consistency,
        'resolution': resolution,
        'claims': claim_urls,
    }


def event_urls(event):
    urls = [str(u) for u in event.get('urls', []) or [] if u]
    for report in event.get('reports', []) or []:
        if isinstance(report, dict):
            for key in ('url', 'link', 'sourceUrl'):
                if report.get(key):
                    urls.append(str(report[key]))
    return list(dict.fromkeys(urls))


def match_canonical(urls, index):
    matched = []
    seen = set()
    for url in urls:
        for event in index['events_by_url'].get(url, []):
            if id(event) not in seen:
                seen.add(id(event))
                matched.append(event)
    return matched[:6]


def match_claims(story_tokens, urls, index):
    out = []
    for claim in index['claims']:
        shared_urls = claim['_urls'] & set(urls)
        overlap = jaccard(story_tokens, claim['_tokens'])
        if shared_urls or overlap >= 0.62:
            out.append((overlap + (0.5 if shared_urls else 0.0), claim))
    out.sort(key=lambda pair: pair[0], reverse=True)
    return [claim for _, claim in out[:5]]


def entity_names(ids, index):
    names = []
    for eid in ids or []:
        entity = index['entities'].get(str(eid))
        if entity and entity.get('canonical_name'):
            name = str(entity['canonical_name']).strip()
            if name and name not in names:
                names.append(name)
    return names[:8]


def story_severity(event, intel, sources, claims, canon_events):
    status = 'active'
    category = str(event.get('category') or 'general').lower()
    score = 0
    if category in ('conflict', 'military', 'security'):
        score += 2
    if BREAKING.search(str(event.get('title') or '')):
        score += 1
    grade = str((intel or {}).get('evidenceGrade') or '')
    if grade in ('A', 'B'):
        score += 1
    independence = str((sources or {}).get('sourceIndependence') or (intel or {}).get('sourceIndependence') or '')
    if independence == 'high':
        score += 1
    if int(event.get('reportCount') or 0) >= 10:
        score += 1
    if any(str(c.get('status')) == 'corroborated' and str(c.get('confidence')) == 'HIGH' for c in claims):
        score += 1
    if len(canon_events) >= 2:
        score += 1
    if score >= 6:
        return 'critical'
    if score >= 4:
        return 'high'
    if score >= 2:
        return 'medium'
    return 'low'


def evidence_rows(event, canon_events, sources, index, limit=8):
    rows = []
    seen = set()

    def add(title, url, source, time='', source_class=''):
        url = str(url or '').strip()
        title = str(title or url or '').strip()
        key = (title.lower(), url.lower())
        if (not title and not url) or key in seen:
            return
        seen.add(key)
        rows.append({'title': title[:300], 'url': url, 'source': str(source or 'Public source')[:120], 'time': str(time or ''), 'sourceClass': source_class})

    for report in event.get('reports', []) or []:
        if isinstance(report, dict):
            add(report.get('title'), report.get('url') or report.get('link'), report.get('source') or report.get('sourceLabel') or report.get('domain'), report.get('published_at') or report.get('time') or report.get('publishedAt'))
    for canon_event in canon_events:
        for eid in canon_event.get('evidence_ids', []) or []:
            ev = index['evidence'].get(str(eid))
            if ev:
                add(ev.get('title'), ev.get('url'), ev.get('source'), ev.get('published_at') or ev.get('time'))
    domain_classes = (sources or {}).get('domainClasses') or {}
    for row in rows:
        for domain, klass in domain_classes.items():
            if domain and domain in row['url']:
                row['sourceClass'] = str(klass)
                break
    return rows[:limit]


def derive_gaps(story, intel, sources, consistency, index):
    gaps = []
    independence = str((sources or {}).get('sourceIndependence') or (intel or {}).get('sourceIndependence') or '')
    independent_groups = int((sources or {}).get('independentReportingGroups') or (intel or {}).get('independentReportingGroups') or 0)
    classes = {str(r.get('sourceClass') or '') for r in story['evidence']}
    primary_like = bool(classes & {'primary', 'major-news', 'wire'})
    story_urls = [r.get('url') for r in story['evidence'] if r.get('url')]

    def gap(gtype, severity, needed):
        gaps.append({
            'id': stable_id('gap', story['id'], gtype),
            'storyId': story['id'],
            'type': gtype,
            'severity': severity,
            'evidenceNeeded': needed,
            '_urls': story_urls[:2],
        })

    if story['slots']['actor'] and not story['slots']['target']:
        gap('no_target', 'high' if story['severity'] in ('critical', 'high') else 'medium', 'A named target role for the reported activity')
    if independent_groups < 2 or independence in ('low', ''):
        gap('single_source', 'high' if story['severity'] in ('critical', 'high') else 'medium', 'At least two independent reporting groups')
    if not primary_like:
        gap('no_primary', 'medium', 'A primary, wire, or major-news source for this story')
    if not story['slots']['geo']:
        gap('no_geo', 'medium', 'A geographic anchor or validated coordinate')
    age = hours_ago(story['lastUpdated'])
    if age is not None and age > 48 and story['status'] != 'resolved':
        gap('stale', 'high' if story['severity'] in ('critical', 'high') else 'low', 'A fresh observation within the last 48 hours')
    flag = consistency.get(str(story['eventId']))
    if flag and (flag.get('flags') or flag.get('contradictions')):
        gap('contradiction', 'critical', 'Resolution of conflicting reports')
    group = index['resolution'].get(str(story['eventId']))
    if group and int(group.get('member_count') or 1) > 1 and 'resolved' not in str(group.get('merge_reason') or '').lower():
        gap('unresolved_duplicate', 'medium', 'Confirmation that this cluster is a single event')
    if not story['slots']['assessment']:
        gap('no_assessment', 'low', 'A published assessment impact for this story')
    return gaps


def lifecycle(current_gaps, prior_index, now):
    out = []
    for gap in current_gaps:
        gid = gap['id']
        prior = prior_index.get(gid)
        state = 'open'
        opened_at = now
        if prior:
            opened_at = prior.get('openedAt') or now
            prior_state = str(prior.get('state') or 'open')
            if prior_state in ('open', 'narrowing'):
                state = prior_state
        out.append({
            'id': gid,
            'storyId': gap['storyId'],
            'type': gap['type'],
            'severity': gap['severity'],
            'state': state,
            'openedAt': opened_at,
            'updatedAt': now,
            'resolvedAt': None,
            'evidenceNeeded': gap['evidenceNeeded'],
            'closingReason': '',
            'closingEvidence': [],
        })
    return out


def close_gap(prior, story, now):
    return {
        'id': prior.get('id'),
        'storyId': story['id'],
        'type': prior.get('type') or 'no_target',
        'severity': prior.get('severity') or 'low',
        'state': 'closed',
        'openedAt': prior.get('openedAt') or now,
        'updatedAt': now,
        'resolvedAt': now,
        'evidenceNeeded': prior.get('evidenceNeeded') or 'Resolved by newer evidence',
        'closingReason': 'The missing piece was satisfied by newer canonical evidence in this refresh.',
        'closingEvidence': story['evidence'][:2] or [{'title': story['title'], 'url': '', 'source': 'Public source', 'time': ''}],
    }


def pressure(story, open_gap_severities):
    severity = SEVERITY_WEIGHT.get(story['severity'], 0.25)
    age = hours_ago(story['lastUpdated'])
    recency = 1.0 if age is not None and age <= 6 else 0.8 if age is not None and age <= 24 else 0.5 if age is not None and age <= 72 else 0.25
    independence = 'high' if story['slots']['corroboration'] else 'limited'
    corroboration = 1.0 if independence == 'high' else 0.4
    gap_weight = 1.0 + min(0.45, 0.15 * sum(1 for s in open_gap_severities if s in ('critical', 'high')))
    return round(min(100.0, 100 * severity * recency * corroboration * gap_weight), 1)


def build_story(event, index, now):
    urls = event_urls(event)
    story_tokens = tokens(event.get('title'))
    canon_events = match_canonical(urls, index)
    actor_ids, target_ids = [], []
    for canon in canon_events:
        actor_ids += canon.get('actor_ids', []) or []
        target_ids += canon.get('target_ids', []) or []
    actors = entity_names(actor_ids, index)
    targets = entity_names(target_ids, index)
    if not actors:
        actors = [str(a).title() for a in (event.get('anchors') or [])[:3]]
    claims = match_claims(story_tokens, urls, index)
    intel = index['event_intel'].get(str(event.get('id')))
    sources = index['source_ev'].get(str(event.get('id')))
    impact = index['impacts'].get(str(event.get('id')))
    first_seen = event.get('firstSeen') or event.get('lastSeen') or now
    last_seen = event.get('lastSeen') or event.get('firstSeen') or now
    age_h = hours_ago(last_seen)
    status = 'active' if age_h is not None and age_h <= 36 else 'dormant' if age_h is None or age_h > 72 else 'narrowing'
    evidence = evidence_rows(event, canon_events, sources, index)
    slots = {
        'actor': bool(actors),
        'target': bool(targets),
        'geo': bool(event.get('anchors')),
        'time': bool(event.get('firstSeen') or event.get('lastSeen')),
        'outcome': str((intel or {}).get('evidenceGrade') or '') in ('A', 'B') or any(str(c.get('status')) == 'corroborated' for c in claims),
        'corroboration': int((sources or {}).get('independentReportingGroups') or 0) >= 2,
        'assessment': impact is not None,
    }
    completeness = round(sum(1 for v in slots.values() if v) / len(SLOT_NAMES), 2)
    grade = str((intel or {}).get('evidenceGrade') or '')
    confidence = GRADE_CONFIDENCE.get(grade, 'unverified')
    if confidence == 'moderate' and not slots['corroboration']:
        confidence = 'limited'
    severity = story_severity(event, intel, sources, claims, canon_events)
    story = {
        'id': stable_id('story', event.get('id')),
        'eventId': str(event.get('id') or ''),
        'title': str(event.get('title') or 'Untitled event cluster')[:240],
        'kind': str(event.get('category') or 'general'),
        'severity': severity,
        'confidence': confidence,
        'status': status,
        'firstSeen': str(first_seen),
        'lastUpdated': str(last_seen),
        'region': ', '.join(str(a) for a in (event.get('anchors') or [])[:3]),
        'actors': actors,
        'targets': targets,
        'hubId': None,
        'hub': '',
        'slots': slots,
        'completeness': completeness,
        'evidence': evidence,
        'evidenceCount': len(evidence),
        'claims': [{'id': c.get('id'), 'claim': str(c.get('claim'))[:200], 'confidence': c.get('confidence'), 'status': c.get('status')} for c in claims],
        'claimIds': [str(c.get('id')) for c in claims if c.get('id')],
        'eventIds': [str(event.get('id'))] + [str(c.get('id')) for c in canon_events],
        'gapIds': [],
        'tensionContribution': 0,
        'reportCount': int(event.get('reportCount') or 0),
    }
    story['gaps'] = derive_gaps(story, intel, sources, index['consistency'], index)
    return story


def link_hubs(stories, brain):
    nodes = [n for n in (brain or {}).get('nodes', []) if isinstance(n, dict)]
    for story in stories:
        haystack = ' '.join([story['title'], story['region'], ' '.join(story['actors']), ' '.join(story['targets'])])
        hay_tokens = tokens(haystack)
        best, best_score = None, 0.0
        for node in nodes:
            label = str(node.get('label') or '').strip()
            if not label:
                continue
            score = 0.0
            if re.search(r'(?<![a-z])' + re.escape(label.lower()) + r'(?![a-z])', haystack.lower()):
                score += 0.6
            node_tokens = tokens(label)
            if node_tokens:
                containment = len(node_tokens & hay_tokens) / max(1, min(len(node_tokens), len(hay_tokens)))
                score += 0.4 * containment
            if score > best_score:
                best, best_score = node, score
        if best and best_score >= 0.2:
            story['hubId'] = str(best.get('id'))
            story['hub'] = str(best.get('label'))


def main():
    live_events = (load('live_events.json', {}) or {}).get('events', [])
    if not isinstance(live_events, list) or not live_events:
        raise SystemExit('BRAIN STORIES BLOCKED: live_events.json has no events')
    prior_doc = load('brain_stories.json', {}) or {}
    prior_gaps = prior_doc.get('gaps', []) if isinstance(prior_doc.get('gaps'), list) else []
    prior_gap_index = {g.get('id'): g for g in prior_gaps if isinstance(g, dict)}
    index = join_indexes()
    now = now_iso()
    stories = [build_story(event, index, now) for event in live_events if isinstance(event, dict)]
    stories.sort(key=lambda s: (SEVERITY_WEIGHT.get(s['severity'], 0), s.get('reportCount', 0), s['lastUpdated']), reverse=True)
    stories = stories[:150]
    link_hubs(stories, load('intelligence_brain.json', {}))

    all_gaps = []
    story_by_id = {s['id']: s for s in stories}
    closed_orphans = []
    for story in stories:
        final_gaps = lifecycle(story.get('gaps', []), prior_gap_index, now)
        for gap in final_gaps:
            gap['storyId'] = story['id']
        story['gapIds'] = [g['id'] for g in final_gaps if g['state'] != 'closed']
        story.pop('gaps', None)
        all_gaps.extend(final_gaps)
        open_sev = [g['severity'] for g in final_gaps if g['state'] != 'closed']
        story['tensionContribution'] = pressure(story, open_sev)
    current_gap_ids = {g['id'] for g in all_gaps}
    for gid, prior in prior_gap_index.items():
        if gid in current_gap_ids or str(prior.get('state')) == 'closed':
            continue
        story = story_by_id.get(str(prior.get('storyId')))
        if story:
            closed = close_gap(prior, story, now)
            all_gaps.append(closed)
            current_gap_ids.add(gid)
        else:
            closed_orphans.append({'id': gid, 'storyId': prior.get('storyId'), 'type': prior.get('type') or 'no_target', 'state': 'closed', 'openedAt': prior.get('openedAt') or now, 'resolvedAt': now})

    open_count = sum(1 for g in all_gaps if g['state'] == 'open')
    narrowing_count = sum(1 for g in all_gaps if g['state'] == 'narrowing')
    closed_count = sum(1 for g in all_gaps if g['state'] == 'closed')
    doc = {
        'version': STORY_SCHEMA_VERSION,
        'updatedAt': now,
        'sourceBackedOnly': True,
        'method': 'Canonical event clusters joined with graded event evidence, source independence, claims, assessments and the Brain hub graph. Gaps are evidence-backed missing pieces with a refresh-to-refresh lifecycle; nothing is generated.',
        'caution': 'Completeness and gap states describe published evidence coverage, not the underlying reality. A closed gap means newer canonical evidence satisfied the slot, not that the story is resolved.',
        'stats': {
            'stories': len(stories),
            'open': open_count,
            'narrowing': narrowing_count,
            'closed': closed_count,
            'withGaps': sum(1 for s in stories if s['gapIds']),
        },
        'stories': stories,
        'gaps': all_gaps,
    }

    history = load('brain_gap_history.json', {}) or {}
    cycles = history.get('cycles', []) if isinstance(history.get('cycles'), list) else []
    prior_history_gaps = history.get('gaps', {}) if isinstance(history.get('gaps'), dict) else {}
    prior_states = {gid: str(entry.get('state')) for gid, entry in prior_history_gaps.items() if isinstance(entry, dict)}
    opened = [g['id'] for g in all_gaps if g['state'] == 'open' and g['id'] not in prior_states]
    closed_now = [g['id'] for g in all_gaps if g['state'] == 'closed']
    reopened = [g['id'] for g in all_gaps if g['state'] == 'open' and prior_states.get(g['id']) == 'closed']
    cycles.append({
        'at': now,
        'stories': len(stories),
        'open': open_count,
        'narrowing': narrowing_count,
        'closed': closed_count,
        'orphanedClosed': len(closed_orphans),
        'opened': opened[:50],
        'closedNow': closed_now[:50],
        'reopened': reopened[:50],
    })
    gap_history = {}
    for orphan in closed_orphans:
        entry = prior_history_gaps.get(orphan['id']) if isinstance(prior_history_gaps.get(orphan['id']), dict) else {}
        transitions = entry.get('history', []) if isinstance(entry.get('history'), list) else []
        transitions.append({'at': now, 'state': 'closed'})
        gap_history[orphan['id']] = {
            'storyId': orphan.get('storyId') or '',
            'type': orphan['type'],
            'state': 'closed',
            'openedAt': orphan['openedAt'],
            'resolvedAt': orphan['resolvedAt'],
            'history': transitions[-40:],
        }
    for gap in all_gaps:
        entry = prior_history_gaps.get(gap['id']) if isinstance(prior_history_gaps.get(gap['id']), dict) else {}
        transitions = entry.get('history', []) if isinstance(entry.get('history'), list) else []
        if not transitions or transitions[-1].get('state') != gap['state']:
            transitions.append({'at': now, 'state': gap['state']})
        gap_history[gap['id']] = {
            'storyId': gap['storyId'],
            'type': gap['type'],
            'state': gap['state'],
            'openedAt': gap['openedAt'],
            'resolvedAt': gap['resolvedAt'],
            'history': transitions[-40:],
        }
    gap_doc = {
        'version': STORY_SCHEMA_VERSION,
        'updatedAt': now,
        'method': 'Gap lifecycle recorded once per canonical refresh; closed entries include the refresh that satisfied them.',
        'cycles': cycles[-200:],
        'gaps': gap_history,
    }

    STORIES.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    GAP_HISTORY.write_text(json.dumps(gap_doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    print(f'BRAIN STORIES: {len(stories)} stories / {open_count} open gaps / {narrowing_count} narrowing / {closed_count} closed this refresh')


if __name__ == '__main__':
    main()
