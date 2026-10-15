"""Checkpoint-native RGB adapters; public interfaces accept RGB and actions only."""
from contextlib import nullcontext
import json
import sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torchvision.transforms import v2
from wm_diag0.core import FeatureContract, Features, array_id, digest, frozen
from .actions import decode,normalize

class PatchEncoder(nn.Module):
    def __init__(self,encoder):
        super().__init__(); self.model=encoder; self.emb_dim=384; self.patch_size=14; self.name='dinov2_vits14'
    def forward(self,x): return self.model.forward_features(x)['x_norm_patchtokens'].float()

class Adapter:
    def __init__(self,task,backbone,source,contract,device='cuda'):
        self.task,self.backbone,self.device=task,backbone,torch.device(device)
        self.source=Path(source); self.c=contract
        prior=Path(contract['prior_source'])
        sys.path[:0]=[str(prior/'lewm'),str(prior/'dino'),str(prior/'encoder')]
        stats=json.loads((prior/('config/'+task+'-stats.json')).read_text())
        self.mean=np.asarray(stats['action_mean'],dtype=np.float64)
        self.std=np.asarray(stats['action_std'],dtype=np.float64)
        if self.mean.shape!=(2,) or self.std.shape!=(2,) or not np.all(self.std>0): raise ValueError('frozen action normalization')
        self.bf16=backbone=='dinowm_noprop'
        if backbone=='lewm':
            self.model=torch.load(contract['lewm'][task]['path'],weights_only=False,map_location='cpu').eval().to(self.device)
            self.transform=v2.Compose([v2.ToImage(),v2.ToDtype(torch.float32,scale=True),v2.Normalize([.485,.456,.406],[.229,.224,.225]),v2.Resize(224)])
            shape=(192,); score='terminal_sum'; checkpoint=contract['lewm'][task]['sha256']
        elif backbone=='dinowm_noprop':
            from dinov2.models.vision_transformer import vit_small
            from models.visual_world_model import VWorldModel
            encoder=vit_small(img_size=518,patch_size=14,init_values=1.,ffn_layer='mlp',block_chunks=0,
                              num_register_tokens=0,interpolate_antialias=False,interpolate_offset=.1)
            encoder.load_state_dict(torch.load(prior/'artifacts/dinov2_vits14.pth',weights_only=True,map_location='cpu'),strict=True)
            bundle=torch.load(prior/('artifacts/'+task+'.pth'),weights_only=False,map_location='cpu')
            from wm_diag0_preflight_v1.worker import validate_dino_structure
            validate_dino_structure(bundle)
            self.model=VWorldModel(image_size=224,num_hist=3,num_pred=1,encoder=PatchEncoder(encoder),
                                  proprio_encoder=bundle['proprio_encoder'],action_encoder=bundle['action_encoder'],
                                  decoder=None,predictor=bundle['predictor'],proprio_dim=10,action_dim=10,concat_dim=1,
                                  num_action_repeat=1,num_proprio_repeat=1,train_encoder=False,train_predictor=False,train_decoder=False)
            self.model.eval(); self.model.to(self.device)
            for m in self.model.modules():
                if hasattr(m,'bias') and torch.is_tensor(m.bias) and not isinstance(m.bias,nn.Parameter): m.bias=m.bias.to(self.device)
            self.transform=v2.Compose([v2.ToImage(),v2.ToDtype(torch.float32,scale=True),v2.Resize(224),v2.CenterCrop(224),v2.Normalize([.5]*3,[.5]*3)])
            shape=(196,384); score='terminal_mse'; checkpoint=contract['prior_members']['artifacts/'+task+'.pth']['sha256']
        else: raise ValueError('fixed backbone')
        self.contract=FeatureContract(backbone,checkpoint,digest({'transform':str(self.transform),'stats':stats,'T':1,'encoder_pin':contract['encoder_pin']}),shape,(5,10,15,20,25),1,score)
        self.cache={}; self.predictor_calls=0; self.encoded_frames=0

    def autocast(self):
        return torch.autocast('cuda',dtype=torch.bfloat16,enabled=self.bf16 and self.device.type=='cuda')

    def pixels(self,rgb):
        rgb=np.asarray(rgb)
        if rgb.dtype!=np.uint8 or rgb.shape[-3:]!=(224,224,3): raise ValueError('RGB-only public input')
        flat=rgb.reshape(-1,224,224,3)
        t=torch.stack([self.transform(torch.from_numpy(np.array(x,copy=True)).permute(2,0,1)) for x in flat])
        return t.reshape(*rgb.shape[:-3],3,224,224).to(self.device)

    @torch.inference_mode()
    def encode_tensor(self,rgb):
        rgb=np.asarray(rgb)
        if rgb.ndim!=4: raise ValueError('batch of native RGB frames')
        x=self.pixels(rgb)[:,None]; self.encoded_frames+=len(rgb)
        if self.backbone=='lewm': z=self.model.encode({'pixels':x})['emb'][:,0]
        else:
            with self.autocast():
                z=self.model.encode_obs({'visual':x,'proprio':torch.zeros(len(rgb),1,1,device=self.device)})['visual'][:,0]
            z=z.float()
        if tuple(z.shape[1:])!=self.contract.feature_shape or not torch.isfinite(z).all(): raise ValueError('native representation shape/finite')
        return z

    def encode(self,rgb): return self.encode_tensor(rgb).detach().float().cpu().numpy()

    def public_info(self,history,goal):
        if np.asarray(history).shape!=(1,224,224,3) or np.asarray(goal).shape!=(224,224,3): raise ValueError('evaluated T=1 context')
        return {'pixels':self.pixels(history)[None], 'goal':self.pixels(np.asarray(goal)[None])[None],
                'action':torch.zeros(1,1,10,device=self.device)}

    def decode(self,z):
        z=np.asarray(z)
        if z.shape[-2:]!=(5,10): raise ValueError('five groups of five two-dimensional actions')
        return decode(z,self.mean,self.std)

    def normalized(self,physical):
        # Candidate actions were decoded in float64 scaler arithmetic and cast
        # by native StandardScaler.inverse_transform to float32. Forecast the
        # retained physical bytes through the matching native forward scaler.
        a=np.asarray(physical)
        return normalize(a,self.mean,self.std)

    @torch.inference_mode()
    def forecast_tensor(self,history,actions):
        a=actions.to(self.device,torch.float32); n,h,d=a.shape
        if (h,d)!=(5,10): raise ValueError('five macro actions')
        if self.backbone=='lewm':
            info={'pixels':self.pixels(history)[None,None].expand(1,n,1,3,224,224)}
            result=self.model.rollout(info,a[None])['predicted_emb'][0,:,1:]
            self.predictor_calls+=5
            return result
        key=array_id(history)
        if key not in self.cache: self.cache={key:self.encode_tensor(history)[:,None]}
        initial=self.cache[key].expand(n,-1,-1,-1)
        wm=self.model
        with self.autocast():
            act=wm.encode_act(a)
            prop=wm.encode_proprio(torch.zeros(n,1,1,device=self.device))
            def tile(t): return t.unsqueeze(2).expand(-1,-1,196,-1)
            z=torch.cat([initial,tile(prop),tile(act[:,:1])],dim=-1)
            outputs=[]
            for t in range(5):
                pred=wm.predict(z[:,-3:])[:,-1:]; self.predictor_calls+=1
                outputs.append(pred[:,0,:,:384].float())
                if t<4:
                    new=torch.cat([pred[...,:-10],tile(act[:,t+1:t+2])],dim=-1)
                    z=torch.cat([z,new],dim=1)
        return torch.stack(outputs,dim=1)

    @torch.inference_mode()
    def costs(self,info,actions):
        # Native solver signature. Only visual history, visual goal, and actions.
        if set(info)-{'pixels','goal','action','_dinowm_hist_z','_dinowm_goal_z'}: raise ValueError('selector information firewall')
        if self.backbone=='lewm': return self.model.get_cost(dict(info),actions)
        wm=self.model; b,s,h,a=actions.shape
        if '_dinowm_hist_z' not in info:
            with self.autocast():
                x=info['pixels'][:,0]
                info['_dinowm_hist_z']=wm.encode_obs({'visual':x,'proprio':torch.zeros(b,1,1,device=self.device)})['visual'].float()
                x=info['goal'][:,0]
                info['_dinowm_goal_z']=wm.encode_obs({'visual':x[:,-1:],'proprio':torch.zeros(b,1,1,device=self.device)})['visual'][:,0].float()
            self.encoded_frames+=2*b
        out=torch.empty(b,s,device=self.device)
        for i in range(b):
            for j in range(0,s,100):
                n=min(100,s-j); act=actions[i,j:j+n].to(self.device,torch.float32)
                with self.autocast():
                    ae=wm.encode_act(act); pe=wm.encode_proprio(torch.zeros(n,1,1,device=self.device))
                    def tile(t): return t.unsqueeze(2).expand(-1,-1,196,-1)
                    z=torch.cat([info['_dinowm_hist_z'][i:i+1].expand(n,-1,-1,-1),tile(pe),tile(ae[:,:1])],dim=-1)
                    for t in range(1,h):
                        pred=wm.predict(z[:,-3:])[:,-1:]; self.predictor_calls+=1
                        z=torch.cat([z,torch.cat([pred[...,:-10],tile(ae[:,t:t+1])],dim=-1)],dim=1)
                    pred=wm.predict(z[:,-3:]); self.predictor_calls+=1
                last=pred[:,-1,:,:384].float()
                out[i,j:j+n]=(last-info['_dinowm_goal_z'][i:i+1]).pow(2).mean((1,2))
        return out

    def get_cost(self,info,actions): return self.costs(info,actions)
    def parameters(self): return self.model.parameters()

    @torch.inference_mode()
    def original_score(self,features,goal):
        if features.contract!=self.contract: raise ValueError('own native S0 representation')
        delta=torch.as_tensor(np.array(features.values[:,-1],copy=True),device=self.device)-torch.as_tensor(np.array(goal,copy=True),device=self.device)
        scores=delta.pow(2).sum(-1) if self.backbone=='lewm' else delta.pow(2).mean((1,2))
        return scores.detach().cpu().numpy()

    def predict(self,history,bank,source_id):
        actions=np.stack([c.actions for c in bank.candidates]); z=self.normalized(actions)
        x=self.forecast_tensor(history,torch.from_numpy(z)).float().cpu().numpy()
        return Features(frozen(x),self.contract,bank.identity,source_id,'predicted')
