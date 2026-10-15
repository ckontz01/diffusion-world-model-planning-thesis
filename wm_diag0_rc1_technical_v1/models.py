"""Unchanged native LeWM adapter with hooks on actual encoder/action/predictor."""
from wm_diag0_campaign_v4.models import Adapter

class CountedLeWM(Adapter):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.backbone!='lewm':raise ValueError('own LeWM route only')
        self.actual=dict(visual_encoder_calls=0,encoded_frames=0,proprio_encoder_calls=0,action_encoder_calls=0,predictor_calls=0);self.hooks=[]
        def visual(m,args):
            if len(args)!=1 or args[0].ndim!=4 or tuple(args[0].shape[1:])!=(3,224,224) or not 1<=args[0].shape[0]<=8:raise ValueError('native LeWM actual visual shape')
            self.actual['visual_encoder_calls']+=1;self.actual['encoded_frames']+=int(args[0].shape[0])
        self.hooks.append(self.model.encoder.register_forward_pre_hook(visual))
        def count(k):
            def hook(m,args):self.actual[k]+=1
            return hook
        for name,k in (('action_encoder','action_encoder_calls'),('predictor','predictor_calls')):self.hooks.append(getattr(self.model,name).register_forward_pre_hook(count(k)))
