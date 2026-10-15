"""New finite usage and supplier-acceptance rejection fixtures, no research data."""
import ast,json,tempfile
from pathlib import Path
from .common import ROOT,DOC,bounds,check_usage,write_new,identity

def reject(fn):
    try:fn()
    except (ValueError,FileNotFoundError):return
    raise AssertionError('missing required rejection')

def local():
    for s in (1,2,3):
        cap=bounds(s);check_usage(s,dict(cap));check_usage(s,{k:0 for k in cap})
        for k in cap:reject(lambda:check_usage(s,dict(cap,**{k:cap[k]+1})))
        reject(lambda:check_usage(s,dict(cap,extra=0)))
        reject(lambda:check_usage(s,{k:v for k,v in cap.items() if k!='encoded_frames'}))
    from .suppliers import head
    for s in (-1,4):reject(lambda:head({},s))
    from .reuse import gate
    with tempfile.TemporaryDirectory(prefix='wm-rc1-artificial-') as tmp:
        reject(lambda:gate({'rc1_technical':{'gate_run':tmp,'gate_seal':{},'gate_report':{}}}))
    src=(ROOT/'wm_diag0_rc1_technical_v1/accept.py').read_text()
    if "parity['additional_sequences']!=0" not in src or 'validate_receipt' not in src or "elif parity['additional_sequences']!=2*n" not in src:raise AssertionError('separate reused vs fresh reference obligations')
    tree=ast.parse((ROOT/'wm_diag0_rc1_technical_v1/reuse.py').read_text())
    obtain=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='obtain')
    forbidden={'predict','forecast_tensor','encode','encode_tensor','costs','solve','rollout'}
    if any(isinstance(x,ast.Attribute) and x.attr in forbidden for x in ast.walk(obtain)):raise AssertionError('reuse cannot run models/CEM')
    files={}
    for p in sorted((ROOT/'wm_diag0_rc1_technical_v1').glob('*.py')):compile(p.read_bytes(),str(p),'exec');files[p.name]=identity(p)
    ast.parse((ROOT/'wm_diag0_rc1_technical_v1/supervisor.py').read_text(),feature_version=(3,6))
    from .operations import STAGE,OBSERVE
    ast.parse('RUN="r"\nGATE="g"\nEXPECTED="e"\n'+STAGE,feature_version=(3,6))
    ast.parse('RUN="r"\n'+OBSERVE,feature_version=(3,6))
    write_new(DOC/'ARTIFICIAL-LOCAL-001.json',{'status':'PASSED','source':files,'research_calls':0,'old_tests_repeated':False,
        'rejections':['every module/frame/API overrun','missing/extra usage key','wrong head setting','missing authenticated gate','reuse cannot call forecast/encode/CEM'],
        'limitations':['real native restore/physics/time/module counts remain included-setting obligations','full scientific aggregates not inspected']})
    print(json.dumps({'status':'RC1_TECHNICAL_ARTIFICIAL_LOCAL_PASSED','research_calls':0}))

def reference():
    import torch
    from torch import nn
    from models.visual_world_model import VWorldModel
    from .reference import NativePointwiseReference
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    class Encoder(nn.Module):
        emb_dim=384;patch_size=14;name='dinov2_artificial'
        def __init__(self):super().__init__();self.batches=[]
        def forward(self,x):self.batches.append(int(x.shape[0]));return x.mean((1,2,3))[:,None,None].expand(-1,196,384)
    class Prop(nn.Module):
        def forward(self,x):return x.expand(*x.shape[:-1],10)
    class Action(nn.Module):
        def forward(self,x):return x
    class Predictor(nn.Module):
        def forward(self,x):return x+x[...,-10:].mean(-1,keepdim=True)/10
    wm=VWorldModel(224,3,1,Encoder(),Prop(),Action(),None,Predictor(),10,10,1,1,1,False,False,False);wm.eval()
    for n in (1,7,16):
        obs={'visual':torch.ones(n,1,3,224,224),'proprio':torch.zeros(n,1,1)};actions=torch.arange(n*50,dtype=torch.float32).reshape(n,5,10)/800
        with torch.inference_mode():
            native,_=wm.rollout(obs,actions);wm.encoder.batches.clear();ref=NativePointwiseReference(wm);result,_=ref.rollout(obs,actions)
        if wm.encoder.batches!=[1]*n or not torch.equal(native['visual'],result['visual']):raise AssertionError('independent original recurrence/ragged pointwise')
        reject(lambda:ref.encode_obs(obs))
        reject(lambda:NativePointwiseReference(wm).encode_obs(dict(obs,proprio=torch.ones(n,1,1))))
    reject(lambda:NativePointwiseReference(wm).encode_obs({'visual':torch.ones(17,1,3,224,224),'proprio':torch.zeros(17,1,1)}))
    print(json.dumps({'status':'NEW_RAGGED_ORIGINAL_METHOD_REFERENCE_ARTIFICIAL_PASSED','research_inputs_loaded':False,'model_downloads':0,'device':'CPU'}))

if __name__=='__main__':
    import sys
    reference() if len(sys.argv)>1 and sys.argv[1]=='reference' else local()
