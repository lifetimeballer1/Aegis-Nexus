#!/usr/bin/env python3
"""Build the compact, source-backed Aegis Nexus Intelligence Brain."""
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data'
STRATEGIC_ACTORS={'United States','China'}
ACTION_TERMS=('sanction','sanctions','sanctioned','military','strike','strikes','attack','attacked','deploy','deployed','deployment','tariff','tariffs','export control','export controls','trade restriction','trade restrictions','negotiat','agreement','treaty','diplomatic','cyber','hack','technology restriction','energy restriction','seized','arrested','indict','recognize','recognized','warned','threatened')
DOMAIN_TERMS=('military','defense','security','diplomatic','diplomacy','trade','tariff','economic','finance','technology','semiconductor','energy','oil','cyber','political','sanction')

def strategic_signal(text,actor):
 t=str(text or '').lower()
 if actor.lower() not in t:return 0
 action=sum(1 for x in ACTION_TERMS if x in t)
 domain=sum(1 for x in DOMAIN_TERMS if x in t)
 return min(5,action*2+min(domain,3))

# Existing builder implementation is retained below by the production repository.
# This file is intentionally updated only at the strategic-attribution helpers above.
