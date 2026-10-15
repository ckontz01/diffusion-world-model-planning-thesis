"""Small new artificial fixtures; no old suite or research input access."""
import ast,json,sys
from pathlib import Path
import numpy as np
from .pointwise import extract

def rejects(fn):
    try:fn()
    except (ValueError,RuntimeError):return
    raise AssertionError('invalid fixture accepted')

def local():
    rgb=np.zeros((8,224,224,3),np.uint8)
    for i in range(8):rgb[i].fill(i)
    calls=[]
    def one(x):
        assert x.shape==(1,224,224,3);calls.append(int(x[0,0,0,0]))
        return np.full((1,196,384),calls[-1],np.float32)
    z=extract(rgb,one,np.concatenate)
    assert calls==list(range(8)) and z.shape==(8,196,384) and z.dtype==np.float32
    calls.clear();zz=extract(rgb[:5],one,np.concatenate)
    assert calls==list(range(5)) and np.array_equal(zz,z[:5])
    rejects(lambda:extract(rgb.astype(np.float32),one,np.concatenate))
    rejects(lambda:extract(rgb[:0],one,np.concatenate))
    rejects(lambda:extract(rgb[:,1:],one,np.concatenate))
    for p in Path(__file__).parent.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
    tree=ast.parse(Path(__file__).with_name('reference.py').read_bytes())
    cl=next(x for x in tree.body if isinstance(x,ast.ClassDef))
    assert {x.name for x in cl.body if isinstance(x,ast.FunctionDef)}=={'__init__','encode_obs'}
    return {'status':'NEW_ARTIFICIAL_POINTWISE_ORDER_SHAPE_AND_STATIC_TESTS_PASSED','research_calls':0,'old56tests_repeated':False}

def reference():
    import torch
    from torch import nn
    from models.visual_world_model import VWorldModel
    from .reference import PointwiseRGBReference
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    class Encoder(nn.Module):
        emb_dim=384;patch_size=14;name='dinov2_artificial'
        def __init__(self):super().__init__();self.batches=[]
        def forward(self,x):
            self.batches.append(x.shape[0])
            return x.mean((1,2,3))[:,None,None].expand(-1,196,384)
    class Prop(nn.Module):
        def forward(self,x):return x.expand(*x.shape[:-1],10)
    class Action(nn.Module):
        def forward(self,x):return x
    class Predictor(nn.Module):
        def forward(self,x):return x+x[...,-10:].mean(-1,keepdim=True)/10
    wm=VWorldModel(224,3,1,Encoder(),Prop(),Action(),None,Predictor(),10,10,1,1,1,False,False,False);wm.eval()
    obs={'visual':torch.ones(16,1,3,224,224),'proprio':torch.zeros(16,1,1)}
    actions=torch.arange(16*5*10,dtype=torch.float32).reshape(16,5,10)/800
    with torch.inference_mode():
        native,_=wm.rollout(obs,actions);wm.encoder.batches.clear()
        ref=PointwiseRGBReference(wm);result,_=ref.rollout(obs,actions)
    assert wm.encoder.batches==[1]*16 and ref.boundary_calls==1
    assert torch.equal(native['visual'],result['visual'])
    rejects(lambda:ref.encode_obs(obs))
    bad=dict(obs,proprio=torch.ones(16,1,1));rejects(lambda:PointwiseRGBReference(wm).encode_obs(bad))
    bad=dict(obs,visual=torch.ones(15,1,3,224,224));rejects(lambda:PointwiseRGBReference(wm).encode_obs(bad))
    bad=dict(obs);bad['visual']=obs['visual'].clone();bad['visual'][1]+=1
    rejects(lambda:PointwiseRGBReference(wm).encode_obs(bad))
    from .models import PointwiseAdapter
    from wm_diag0_campaign_v4.models import Adapter
    assert PointwiseAdapter.forecast_tensor is Adapter.forecast_tensor and PointwiseAdapter.costs is Adapter.costs
    return {'status':'NEW_ARTIFICIAL_ORIGINAL_METHOD_POINTWISE_REFERENCE_TESTS_PASSED','research_calls':0,'model_downloads':0,'device':'CPU'}

if __name__=='__main__':print(json.dumps(reference() if len(sys.argv)>1 and sys.argv[1]=='reference' else local()))
