"""Artificial tests only; no research artifacts, data, GPU or model loads."""
import ast,json,sys
from pathlib import Path
import numpy as np
from .metrics import compare,check_metric,decision

def rejects(fn):
    try:fn()
    except (ValueError,RuntimeError):return
    raise AssertionError('fixture incorrectly accepted')

def local():
    a=np.zeros((5,196,384),dtype=np.float32);b=a.copy()
    assert compare(a,b)['exact_bits'];b[0,0,0]=.1
    assert compare(a,b)['mismatched_elements']==1
    check_metric(compare(a,b),a.shape)
    rejects(lambda:compare(a,a.astype(np.float64)))
    rejects(lambda:compare(a,a[:1]))
    bad=a.copy();bad[0,0,0]=np.nan;rejects(lambda:compare(a,bad))
    z=np.zeros(1,dtype=np.float32);minus=-z
    assert not compare(z,minus)['exact_bits'] and compare(z,minus)['within_original_tolerance']
    row=compare(a,a);row['mismatched_elements']=1;rejects(lambda:check_metric(row,a.shape))
    report={'roles':{},'conditional':{}}
    for task in ('pusht','reacher'):
        report['roles'][task]={'comparisons':{str(i)+'-'+k:compare(a,a) for i in (0,1) for k in ('1v5','1v8','5v8')},
            'repeats':{k:compare(np.zeros((8 if k=='8' else 5,196,384),np.float32),np.zeros((8 if k=='8' else 5,196,384),np.float32)) for k in ('1','5','8')}}
    for k,s in [('source_cache',(1,1,196,384)),('goal',(196,384)),('forecast',(16,5,196,384)),('cached_cost',(16,)),('terminal_cost',(1,16))]:
        x=np.zeros(s,np.float32);report['conditional'][k]=compare(x,x)
    assert decision(report)['all_numerical_checks_passed']
    report['roles']['pusht']['comparisons']['0-1v5']=compare(a,b)
    assert not decision(report)['all_numerical_checks_passed'] and decision(report)['conditional_recurrence_passed']
    del report['roles']['pusht']['comparisons']['1-5v8'];rejects(lambda:decision(report))
    tree=ast.parse((Path(__file__).with_name('reference.py')).read_text())
    cl=[x for x in tree.body if isinstance(x,ast.ClassDef)][0]
    assert {x.name for x in cl.body if isinstance(x,ast.FunctionDef)}=={'__init__','encode_obs'}
    for p in Path(__file__).parent.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
    return {'status':'ARTIFICIAL_ARRAY_SCHEMA_AND_STATIC_CHECKS_PASSED','real_checkpoints_loaded':0,'old_56_tests_repeated':False}

def reference():
    import torch
    from torch import nn
    from models.visual_world_model import VWorldModel
    from .reference import CanonicalVisualReference
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    class Encoder(nn.Module):
        emb_dim=384;patch_size=14;name='dinov2_artificial'
        def forward(self,x):return torch.zeros(x.shape[0],196,384)
    class Prop(nn.Module):
        def forward(self,x):return x.expand(*x.shape[:-1],10)
    class Action(nn.Module):
        def forward(self,x):return x
    class Predictor(nn.Module):
        def forward(self,x):return x+x[...,-10:].mean(-1,keepdim=True)/10
    wm=VWorldModel(224,3,1,Encoder(),Prop(),Action(),None,Predictor(),10,10,1,1,1,False,False,False);wm.eval()
    rgb=torch.zeros(1,1,3,224,224);canonical=torch.zeros(1,1,196,384)
    ref=CanonicalVisualReference(wm,canonical,rgb)
    obs={'visual':rgb.expand(16,-1,-1,-1,-1),'proprio':torch.zeros(16,1,1)}
    actions=torch.arange(16*5*10,dtype=torch.float32).reshape(16,5,10)/800
    with torch.inference_mode():
        native,_=wm.rollout(obs,actions);reconstructed,_=ref.rollout(obs,actions)
    assert torch.equal(native['visual'],reconstructed['visual'])
    from contextlib import nullcontext
    from wm_diag0_campaign_v4.models import Adapter
    class ArtificialAdapter:
        forecast_tensor=Adapter.forecast_tensor
        backbone='dinowm_noprop';device=torch.device('cpu');predictor_calls=0
        def autocast(self):return nullcontext()
        def encode_tensor(self,history):return canonical[:,0]
    adapter=ArtificialAdapter();adapter.model=wm;adapter.cache={}
    with torch.inference_mode():production=adapter.forecast_tensor(np.zeros((1,224,224,3),np.uint8),actions)
    assert torch.equal(production,native['visual'][:,1:]) and adapter.predictor_calls==5
    rejects(lambda:ref.encode_obs(obs))
    ref=CanonicalVisualReference(wm,canonical,rgb);changed=dict(obs,visual=torch.ones(16,1,3,224,224));rejects(lambda:ref.encode_obs(changed))
    ref=CanonicalVisualReference(wm,canonical,rgb);rejects(lambda:ref.encode_obs(dict(obs,proprio=torch.ones(16,1,1))))
    rejects(lambda:CanonicalVisualReference(wm,canonical[:,:,:,:383],rgb))
    rejects(lambda:CanonicalVisualReference(wm,canonical.double(),rgb))
    # A wrong canonical input is detectably non-equivalent, never an automatic pass.
    wrong=CanonicalVisualReference(wm,canonical+1,rgb)
    with torch.inference_mode():other,_=wrong.rollout(obs,actions)
    assert not torch.equal(native['visual'],other['visual'])
    return {'status':'ARTIFICIAL_PINNED_NATIVE_REFERENCE_AND_REJECTION_CHECKS_PASSED','real_checkpoints_loaded':0,'research_forwards':0,'device':'CPU'}

if __name__=='__main__':print(json.dumps(reference() if len(sys.argv)>1 and sys.argv[1]=='reference' else local()))
