#!/usr/bin/env python3
"""Canonical event pipeline replacing the five independent event build stages."""
from __future__ import annotations
import importlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STAGES=(
 ('history','build_event_history'),
 ('intelligence','build_event_intelligence'),
 ('consistency','build_event_consistency'),
 ('resolution','build_event_resolution'),
 ('market_impact','build_event_market_impact'),
)
def run():
    completed=[]
    for name,module_name in STAGES:
        module=importlib.import_module(module_name)
        main=getattr(module,'main',None)
        if not callable(main):raise RuntimeError(f'{module_name} has no main() entry point')
        print(f'=== EVENT PIPELINE: {name} ===',flush=True);main();completed.append(name)
    return completed
if __name__=='__main__':
    result=run();print('EVENT PIPELINE PASSED:',', '.join(result),flush=True)
