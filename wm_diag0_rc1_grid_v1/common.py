from wm_diag0_rc1_technical_v1.common import ROOT,BASE,OLD_RUN,HEADS_RUN,GATE_RUN,SETTINGS,identity,write_new,canonical
from wm_diag0_rc1_technical_v1.common import RUN as TECHNICAL_RUN
DOCREL='docs/world-model-diagnostic-rc1-grid-v1-20261016'
DOC=ROOT/DOCREL
RUN=BASE+'/campaign-v4-rc1-grid-v1'

def setting(index):
    if type(index) is not int or not 0<=index<124:raise ValueError('fixed124 grid indices')
    return index//31,1+index%31

def bounds(i):
    s,_=setting(i)
    if s%2:return dict(visual_encoder_calls=148,encoded_frames=148,proprio_encoder_calls=3119,action_encoder_calls=2971,predictor_calls=14855,cost_api_calls=991)
    return dict(visual_encoder_calls=1998,encoded_frames=2062,proprio_encoder_calls=0,action_encoder_calls=5946,predictor_calls=4955,cost_api_calls=991)

def check_usage(index,usage):
    cap=bounds(index)
    if set(usage)!=set(cap) or any(type(usage[k]) is not int or not 0<=usage[k]<=v for k,v in cap.items()):raise ValueError('actual ordinary-parent invocation bounds')

def gates(c):
    from pathlib import Path
    import json
    for k,x in c['rc1_grid']['technical_suppliers'].items():
        p=Path(x['run'])/'tasks'/('technical-'+k)
        if identity(p/'controls/ACCEPTED.json')!=x['acceptance_identity'] or identity(p/'output/MEMBERS.json')!=x['output_seal']:raise ValueError('all four independently accepted setting suppliers')
        a=json.loads((p/'controls/ACCEPTED.json').read_text());r=json.loads((p/'controls/RESULT.json').read_text())
        if not a['accepted'] or r['status']!='ACCEPTED' or a['output_seal']!=x['output_seal']:raise ValueError('included setting acceptance')
        expected=r.get('acceptance_identity',{'sha256':r.get('acceptance_sha256')})
        if expected['sha256']!=x['acceptance_identity']['sha256']:raise ValueError('accepted setting result chain')
    if set(c['rc1_grid']['technical_suppliers'])!={'0','1','2','3'}:raise ValueError('all four gates required')
