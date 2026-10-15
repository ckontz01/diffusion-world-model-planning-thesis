"""Independently encode RGB B1 with original methods, inherit all recurrence."""
import torch
from models.visual_world_model import VWorldModel

class PointwiseRGBReference(VWorldModel):
    def __init__(self,original):
        if type(original) is not VWorldModel:raise ValueError('exact pinned native class')
        if (original.num_hist,original.num_pred,original.concat_dim,original.action_dim,original.proprio_dim,
            original.num_action_repeat,original.num_proprio_repeat)!=(3,1,1,10,10,1,1):raise ValueError('native recurrence contract')
        if any(m.training for m in original.modules()):raise ValueError('evaluation state required')
        super().__init__(image_size=224,num_hist=3,num_pred=1,encoder=original.encoder,
            proprio_encoder=original.proprio_encoder,action_encoder=original.action_encoder,
            decoder=None,predictor=original.predictor,proprio_dim=10,action_dim=10,concat_dim=1,
            num_action_repeat=1,num_proprio_repeat=1,train_encoder=False,train_predictor=False,train_decoder=False)
        self.eval();self.boundary_calls=0
        for name in ('rollout','encode','encode_act','encode_proprio','predict','replace_actions_from_z','separate_emb'):
            if getattr(type(self),name) is not getattr(VWorldModel,name):raise ValueError('original method inheritance')

    def encode_obs(self,obs):
        if set(obs)!={'visual','proprio'} or self.boundary_calls:raise ValueError('one explicit RGB reference boundary')
        if tuple(obs['visual'].shape)!=(16,1,3,224,224) or tuple(obs['proprio'].shape)!=(16,1,1):raise ValueError('fixed16candidate T1 RGB')
        if torch.count_nonzero(obs['proprio']):raise ValueError('only frozen zero proprio')
        if any(not torch.equal(obs['visual'][i:i+1],obs['visual'][:1]) for i in range(1,16)):
            raise ValueError('retained bank same original source RGB')
        self.boundary_calls+=1
        encoded=[VWorldModel.encode_obs(self,{k:v[i:i+1] for k,v in obs.items()}) for i in range(16)]
        if any(set(x)!={'visual','proprio'} for x in encoded):raise ValueError('native encoded state keys')
        return {k:torch.cat([x[k] for x in encoded],dim=0) for k in ('visual','proprio')}
