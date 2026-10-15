"""Only encode_obs is replaced; all native recurrence methods are inherited.

Import only after the adapter selects its authenticated source closure.
No adapter trajectory, action encoding, proprio encoding or mutable cache enters.
"""
import torch
from models.visual_world_model import VWorldModel

class CanonicalVisualReference(VWorldModel):
    def __init__(self, original, canonical_visual, original_pixels):
        if type(original) is not VWorldModel:raise ValueError('exact pinned native constructor')
        if (original.num_hist,original.num_pred,original.concat_dim,original.action_dim,original.proprio_dim,
            original.num_action_repeat,original.num_proprio_repeat)!=(3,1,1,10,10,1,1):raise ValueError('native recurrence contract')
        if tuple(canonical_visual.shape)!=(1,1,196,384) or canonical_visual.dtype!=torch.float32 or not torch.isfinite(canonical_visual).all():
            raise ValueError('canonical visual boundary')
        if tuple(original_pixels.shape)!=(1,1,3,224,224):raise ValueError('T=1 raw visual binding')
        if any(m.training for m in original.modules()):raise ValueError('read-only evaluation modules')
        super().__init__(image_size=224,num_hist=3,num_pred=1,encoder=original.encoder,
            proprio_encoder=original.proprio_encoder,action_encoder=original.action_encoder,
            decoder=None,predictor=original.predictor,proprio_dim=10,action_dim=10,concat_dim=1,
            num_action_repeat=1,num_proprio_repeat=1,train_encoder=False,train_predictor=False,train_decoder=False)
        self.eval()
        self._canonical_visual=canonical_visual.detach().clone()
        self._original_pixels=original_pixels.detach().clone()
        self.boundary_calls=0
        for name in ('rollout','encode','encode_act','encode_proprio','predict','replace_actions_from_z','separate_emb'):
            if getattr(type(self),name) is not getattr(VWorldModel,name):raise ValueError('native method inheritance')

    def encode_obs(self, obs):
        if set(obs)!={'visual','proprio'} or self.boundary_calls:raise ValueError('single explicit reference boundary')
        n=obs['visual'].shape[0]
        if n!=16 or tuple(obs['visual'].shape)!=(16,1,3,224,224) or tuple(obs['proprio'].shape)!=(16,1,1):
            raise ValueError('fixed 16-candidate T1 context')
        if not torch.equal(obs['visual'],self._original_pixels.expand(n,-1,-1,-1,-1)) or torch.count_nonzero(obs['proprio']):
            raise ValueError('original source pixels and allowed zero proprio only')
        self.boundary_calls+=1
        return {'visual':self._canonical_visual.expand(n,-1,-1,-1),
                'proprio':self.encode_proprio(obs['proprio'])}
