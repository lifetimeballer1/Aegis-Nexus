#!/usr/bin/env python3
"""Fail-closed validation for data/brain_stories.json (B4)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from brain_schema import validate_stories

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'data' / 'brain_stories.json'


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    path = Path(argv[0]) if argv and not argv[0].startswith('-') else STORE
    if not path.is_file():
        print(f'BRAIN STORIES FAILED: missing {path.name}')
        return 1
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        print(f'BRAIN STORIES FAILED: invalid JSON: {exc}')
        return 1
    errors = validate_stories(doc)
    if errors:
        print('BRAIN STORIES FAILED:')
        for error in errors[:20]:
            print(f'  - {error}')
        return 1
    stories = doc.get('stories') or []
    gaps = doc.get('gaps') or []
    print(f'BRAIN STORIES PASSED: stories={len(stories)} gaps={len(gaps)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
