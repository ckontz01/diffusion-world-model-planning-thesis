"""Same original-method pointwise reference, allowing fixed ragged n<=16 bank."""
import torch
from models.visual_world_model import VWorldModel
from wm_diag0_rc1_v1.reference import PointwiseRGBReference

class NativePointwiseReference(PointwiseRGBReference):
    def encode_obs(self,obs):
        if set(obs)!={'visual','proprio'} or self.boundary_calls:raise ValueError('one independent RGB reference boundary')
        n=int(obs['visual'].shape[0])
        if not 1<=n<=16 or tuple(obs['visual'].shape)!=(n,1,3,224,224) or tuple(obs['proprio'].shape)!=(n,1,1):raise ValueError('ragged fixed-bank T1 RGB')
        if torch.count_nonzero(obs['proprio']) or any(not torch.equal(obs['visual'][i:i+1],obs['visual'][:1]) for i in range(1,n)):raise ValueError('one source/zero proprio')
        self.boundary_calls+=1
        encoded=[VWorldModel.encode_obs(self,{k:v[i:i+1] for k,v in obs.items()}) for i in range(n)]
        if any(set(z)!={'visual','proprio'} for z in encoded):raise ValueError('original native states')
        return {k:torch.cat([z[k] for z in encoded],dim=0) for k in ('visual','proprio')}
