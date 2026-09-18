"""New LGP1 model definitions; no old checkpoint conversion or training runner.

Common information, decoder width/depth; not identical parameter count/FLOPs.
Tensor-only synthetic use is safe. Research fitting requires separate approval.
"""
import math
import torch
from torch import nn
import torch.nn.functional as F


class LocalProposer(nn.Module):
    def __init__(self, family, width=512, depth=3, heads=8):
        super().__init__()
        if family not in ('gmm','diffusion'):
            raise ValueError('Unknown family')
        self.family = family
        self.visual = nn.Sequential(nn.LayerNorm(192),nn.Linear(192,width))
        self.types = nn.Parameter(torch.zeros(1,5,width))
        self.state = nn.Sequential(nn.Linear(11,width),nn.SiLU(),nn.Linear(width,width))
        self.clock = nn.Sequential(nn.Linear(3,width),nn.SiLU(),nn.Linear(width,width))
        self.query = nn.Parameter(torch.randn(1,3,width)*.02)
        self.decoder = nn.TransformerDecoder(nn.TransformerDecoderLayer(
            width,heads,4*width,dropout=0,activation='gelu',batch_first=True,norm_first=True),depth)
        self.norm = nn.LayerNorm(width)
        if family == 'gmm':
            self.logits = nn.Linear(width,8)
            self.mean = nn.Linear(width,80)
            self.log_std = nn.Linear(width,80)
        else:
            self.noisy = nn.Linear(10,width)
            self.time = nn.Sequential(nn.Linear(5,width),nn.SiLU(),nn.Linear(width,width))
            self.velocity = nn.Linear(width,10)

    def forward(self, history, local, far, lowdim, remaining, noisy=None, timestep=None):
        b = history.shape[0]
        if (history.shape != (b,3,192) or local.shape != (b,1,192) or
            far.shape != (b,1,192) or lowdim.shape != (b,11) or remaining.shape != (b,)):
            raise ValueError('Invalid condition shape')
        if not all(torch.isfinite(x).all() for x in (history,local,far,lowdim,remaining)):
            raise ValueError('Nonfinite condition')
        if (remaining < 15).any() or (remaining > 150).any():
            raise ValueError('Invalid cycle clock')
        clock = torch.stack([remaining/150,torch.full_like(remaining,.1),15/remaining],-1)
        mem = torch.cat([self.visual(torch.cat([history,local,far],1))+self.types,
                         self.state(lowdim)[:,None],self.clock(clock)[:,None]],1)
        query = self.query.expand(b,-1,-1)
        if self.family == 'diffusion':
            if noisy is None or timestep is None or noisy.shape != (b,3,10) or timestep.shape != (b,):
                raise ValueError('Diffusion needs noisy action and time')
            t = timestep.float()/999
            tf = torch.stack([t,torch.sin(math.pi*t),torch.cos(math.pi*t),
                              torch.sin(2*math.pi*t),torch.cos(2*math.pi*t)],-1)
            query = query+self.noisy(noisy)+self.time(tf)[:,None]
        hidden = self.norm(self.decoder(query,mem))
        if self.family == 'diffusion':
            return self.velocity(hidden)
        return (self.logits(hidden.mean(1)),self.mean(hidden).reshape(b,3,8,10).transpose(1,2),
                self.log_std(hidden).reshape(b,3,8,10).transpose(1,2).clamp(-5,1))


def gmm_nll(outputs, action):
    logits,mean,log_std = outputs
    lp = (-.5*((action[:,None]-mean)*torch.exp(-log_std))**2-log_std-.5*math.log(2*math.pi)).sum((-1,-2))
    return -torch.logsumexp(F.log_softmax(logits,-1)+lp,-1)  # per-row loss


def cosine_alpha():
    t = torch.linspace(0,1000,1001,dtype=torch.float64)
    f = torch.cos(((t/1000+.008)/1.008)*math.pi/2)**2
    f = f/f[0]
    return torch.cumprod(1-(1-f[1:]/f[:-1]).clamp(1e-5,.999),0).float()


def velocity_loss(model, inputs, clean, noise, timestep):
    a = cosine_alpha().to(clean.device)[timestep][:,None,None]
    noisy = a.sqrt()*clean+(1-a).sqrt()*noise
    target = a.sqrt()*noise-(1-a).sqrt()*clean
    return (model(*inputs,noisy=noisy,timestep=timestep)-target).square().mean((1,2))


@torch.no_grad()
def sample(model, inputs, count, rng):
    if count < 1:
        raise ValueError('Empty bank')
    b = inputs[0].shape[0]
    if model.family == 'gmm':
        logits,means,log_std = model(*inputs)
        # Inverse-CDF categorical draw avoids CUDA multinomial's strict-
        # determinism restriction; one shared mode per whole trajectory.
        u=torch.rand((b,count),device=logits.device,generator=rng)
        cumulative=logits.softmax(-1).cumsum(-1);cumulative[:,-1]=1
        modes=(u[:,:,None]>cumulative[:,None]).sum(-1)
        rows = torch.arange(b,device=means.device)[:,None]
        mean,std = means[rows,modes],log_std[rows,modes].exp()
        return mean+std*torch.randn(mean.shape,device=mean.device,generator=rng)
    expanded = tuple(x[:,None].expand(b,count,*x.shape[1:]).reshape(b*count,*x.shape[1:]) for x in inputs)
    x = torch.randn((b*count,3,10),device=inputs[0].device,generator=rng)
    alpha = cosine_alpha().to(x.device)
    indices = (999,749,500,250,0)
    for position,index in enumerate(indices):
        a = alpha[index]
        v = model(*expanded,noisy=x,timestep=torch.full((len(x),),index,device=x.device))
        clean,noise = a.sqrt()*x-(1-a).sqrt()*v,(1-a).sqrt()*x+a.sqrt()*v
        if position+1 == len(indices):
            x = clean
        else:
            next_a = alpha[indices[position+1]]
            x = next_a.sqrt()*clean+(1-next_a).sqrt()*noise
    return x.reshape(b,count,3,10)
