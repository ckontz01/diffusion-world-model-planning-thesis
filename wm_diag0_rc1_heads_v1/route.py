"""Expected amended route derives from authenticated ORIGINAL head contract."""
from dataclasses import replace
import json
from pathlib import Path
from wm_diag0.core import FeatureContract,digest
from wm_diag0_native_v3.store import authenticate
from .common import REPRESENTATION,identity,canonical

def amend(original):
    return replace(original,preprocessing_sha256=digest({'original_preprocessing_sha256':original.preprocessing_sha256,
        'representation':REPRESENTATION,'image_batch':1,'T':1,'concatenate_after_extraction':True}))

def original(c,setting):
    if setting not in (1,3):raise ValueError('exact two DINO settings only')
    key='readout-'+str(setting);t=Path(c['recovery']['old_run'])/'tasks'/key
    supplier=c['recovery']['accepted_suppliers'][key]
    if identity(t/'controls/ACCEPTED.json')!=supplier['control']:raise ValueError('accepted original head control')
    authenticate(t/'output',supplier['output_seal'],140_000_000)
    meta=json.loads((t/'output/READOUT.json').read_text())
    if meta['task']!=('pusht' if setting==1 else 'reacher') or meta['backbone']!='dinowm_noprop':raise ValueError('old own DINO head')
    d=dict(meta['contract']);d['feature_shape']=tuple(d['feature_shape']);d['positions']=tuple(d['positions'])
    old=FeatureContract(**d)
    if old.feature_shape!=(196,384) or old.history_length!=1 or old.positions!=(5,10,15,20,25):raise ValueError('original native feature contract')
    return old

def require(actual,expected):
    if canonical(actual.__dict__)!=canonical(expected.__dict__):raise ValueError('exact independently bound pointwise readout route')

def check(c,setting,actual):
    require(actual,amend(original(c,setting)))
