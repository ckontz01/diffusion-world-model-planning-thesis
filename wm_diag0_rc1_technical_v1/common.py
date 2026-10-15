from wm_diag0_rc1_heads_v1.common import ROOT,BASE,OLD_RUN,GATE_RUN,REPRESENTATION,identity,write_new,canonical
from wm_diag0_rc1_heads_v1.common import RUN as HEADS_RUN
DOCREL='docs/world-model-diagnostic-rc1-technical-v1-20261016'
DOC=ROOT/DOCREL
RUN=BASE+'/campaign-v4-rc1-technical-v1'
SETTINGS=(('pusht','lewm'),('pusht','dinowm_noprop'),('reacher','lewm'),('reacher','dinowm_noprop'))

def bounds(setting):
    if setting==1:return dict(visual_encoder_calls=144,encoded_frames=144,proprio_encoder_calls=3024,action_encoder_calls=2880,predictor_calls=14400,cost_api_calls=960)
    if setting==2:return dict(visual_encoder_calls=2002,encoded_frames=2066,proprio_encoder_calls=0,action_encoder_calls=5958,predictor_calls=4965,cost_api_calls=993)
    if setting==3:return dict(visual_encoder_calls=166,encoded_frames=166,proprio_encoder_calls=3138,action_encoder_calls=2977,predictor_calls=14865,cost_api_calls=993)
    raise ValueError('only three remaining technical settings')

def check_usage(setting,usage):
    cap=bounds(setting)
    if set(usage)!=set(cap) or any(type(usage[k]) is not int or not 0<=usage[k]<=v for k,v in cap.items()):raise ValueError('actual module/frame/API bound')
