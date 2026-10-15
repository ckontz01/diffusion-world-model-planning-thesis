"""DINO pointwise extraction; original source/goal/cost/recurrence inherited."""
from dataclasses import replace
import time
import torch
from wm_diag0_campaign_v4.models import Adapter
from wm_diag0.core import digest
from .pointwise import extract
from .common import REPRESENTATION

class PointwiseAdapter(Adapter):
    def __init__(self,task,backbone,source,contract,device='cuda'):
        if backbone!='dinowm_noprop':raise ValueError('DINO-only amendment')
        super().__init__(task,backbone,source,contract,device)
        self.original_contract=self.contract
        self.contract=replace(self.contract,preprocessing_sha256=digest({'original_preprocessing_sha256':self.contract.preprocessing_sha256,
            'representation':REPRESENTATION,'image_batch':1,'T':1,'concatenate_after_extraction':True}))
        self.single_image_seconds=[]
        self.actual=dict(visual_encoder_calls=0,encoded_frames=0,proprio_encoder_calls=0,action_encoder_calls=0,predictor_calls=0)
        self.hooks=[]
        def visual(module,args):
            if len(args)!=1 or tuple(args[0].shape)!=(1,3,196,196):raise ValueError('actual encoder must see B1/T1 native196')
            self.actual['visual_encoder_calls']+=1;self.actual['encoded_frames']+=1
        self.hooks.append(self.model.encoder.model.patch_embed.register_forward_pre_hook(visual))
        def count(key):
            def hook(module,args):self.actual[key]+=1
            return hook
        for name,key in (('proprio_encoder','proprio_encoder_calls'),('action_encoder','action_encoder_calls'),('predictor','predictor_calls')):
            self.hooks.append(getattr(self.model,name).register_forward_pre_hook(count(key)))

    @torch.inference_mode()
    def encode_tensor(self,rgb):
        def one(frame):
            if self.device.type=='cuda':torch.cuda.synchronize(self.device)
            began=time.monotonic()
            z=Adapter.encode_tensor(self,frame)
            if self.device.type=='cuda':torch.cuda.synchronize(self.device)
            self.single_image_seconds.append(time.monotonic()-began)
            return z
        return extract(rgb,one,lambda outputs:torch.cat(outputs,dim=0))
