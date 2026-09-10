#!/usr/bin/env python3
"""Fail-closed validation for data/brain_gap_history.json (B4)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from brain_schema import validate_gap_history

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'data' / 'brain_gap_history.json'


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    path = Path(argv[0]) if argv and not argv[0].startswith('-') else STORE
    if not path.is_file():
        print(f'BRAIN GAP HISTORY FAILED: missing {path.name}')
        return 1
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        print(f'BRAIN GAP HISTORY FAILED: invalid JSON: {exc}')
        return 1
    errors = validate_gap_history(doc)
    if errors:
        print('BRAIN GAP HISTORY FAILED:')
        for error in errors[:20]:
            print(f'  - {error}')
        return 1
    cycles = doc.get('cycles') or []
    gaps = doc.get('gaps') or {}
    states = {'open': 0, 'narrowing': 0, 'closed': 0}
    for entry in gaps.values():
        if isinstance(entry, dict) and entry.get('state') in states:
            states[entry['state']] += 1
    print(f'BRAIN GAP HISTORY PASSED: cycles={len(cycles)} gaps={len(gaps)} open={states["open"]} narrowing={states["narrowing"]} closed={states["closed"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
