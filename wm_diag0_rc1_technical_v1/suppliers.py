"""Authenticate mixed original-LeWM/new-RC1-DINO head suppliers, no refitting."""
import json
from pathlib import Path
from .common import identity
from wm_diag0_native_v3.store import authenticate

def head(c,setting):
    if setting in (0,2):
        t=Path(c['recovery']['old_run'])/'tasks'/('readout-'+str(setting));s=c['recovery']['accepted_suppliers']['readout-'+str(setting)]
        ctl=s['control'];seal=s['output_seal']
    elif setting in (1,3):
        t=Path(c['rc1_technical']['heads_run'])/'tasks'/('readout-'+str(setting));s=c['rc1_technical']['head_suppliers'][str(setting)]
        ctl=s['acceptance_identity'];seal=s['output_seal']
    else:raise ValueError('four fixed head settings')
    if identity(t/'controls/ACCEPTED.json')!=ctl:raise ValueError('head accepted control identity')
    a=json.loads((t/'controls/ACCEPTED.json').read_text())
    if not a['accepted'] or a['output_seal']!=seal:raise ValueError('head acceptance/seal')
    authenticate(t/'output',seal,140_000_000)
    return t/'output',seal
