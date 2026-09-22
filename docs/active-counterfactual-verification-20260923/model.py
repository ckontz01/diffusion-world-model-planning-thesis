"""Four-component neural response/continuation model. NumPy analytic gradients.

No ID features, table lookup, optimizer at inference, checkpoint loader for
research models, Gaussian contrast compression, or environment dependency.
"""
import json
from pathlib import Path
import numpy as np
from tree import finite


def sigmoid(x):
    e=np.exp(-np.abs(x));return np.where(x>=0,1/(1+e),e/(1+e))


def logsumexp(x):
    m=x.max(-1,keepdims=True);return m+np.log(np.exp(x-m).sum(-1,keepdims=True))


def softmax(x):return np.exp(x-logsumexp(x))


class MLP:
    def __init__(self,dims,rng):
        self.dims=tuple(dims)
        self.params=[]
        for a,b in zip(dims[:-1],dims[1:]):
            self.params.extend([rng.normal(0,np.sqrt(2/(a+b)),(a,b)),np.zeros(b)])

    def forward(self,x):
        activations=[finite(x)]
        for i in range(len(self.params)//2):
            y=activations[-1]@self.params[2*i]+self.params[2*i+1]
            activations.append(np.tanh(y) if i<len(self.params)//2-1 else y)
        finite(activations[-1]);return activations[-1],activations

    def backward(self,d,cache):
        grads=[None]*len(self.params)
        for i in reversed(range(len(self.params)//2)):
            if i<len(self.params)//2-1:d=d*(1-cache[i+1]**2)
            grads[2*i]=cache[i].T@d;grads[2*i+1]=d.sum(0)
            d=d@self.params[2*i].T
        return d,grads


class Preprocessing:
    """Fitting-source-only statistics; source identity is provenance, never input."""
    def __init__(self,xmean,xstd,amean,astd,rmean,rstd,fit_ids):
        self.xmean=xmean;self.xstd=xstd;self.amean=amean;self.astd=astd
        self.rmean=rmean;self.rstd=rstd;self.fit_ids=tuple(fit_ids)

    @classmethod
    def fit(cls,data):
        if set(data['roles'])!={'fit'}:raise ValueError('Preprocessing may fit only fitting sources')
        active=data['terminal']==2
        if not active.any():raise ValueError('Need active training observations')
        def stats(x):
            x=finite(x);mean=x.mean(0);sd=x.std(0);return mean,np.where(sd<1e-6,1,sd)
        return cls(*stats(data['x']),*stats(data['a'][data['mask']]),
                   *stats(data['r'][active]),sorted(set(data['source_ids'])))

    def transform(self,x,a,r=None):
        xx=(finite(x)-self.xmean)/self.xstd
        aa=(finite(a)-self.amean)/self.astd
        rr=None if r is None else (finite(r)-self.rmean)/self.rstd
        return xx,aa,rr


def row_weights(data):
    """One source unit, split over its observed prefixes (not suffix rows)."""
    ids=np.asarray(data['source_ids']);unique,counts=np.unique(ids,return_counts=True)
    sizes=dict(zip(unique,counts))
    return np.array([1/(len(unique)*sizes[s]) for s in ids])


class JointModel:
    def __init__(self,xdim,adim,rdim,seed=94011,width=32,preprocessing=None):
        self.xdim=xdim;self.adim=adim;self.rdim=rdim;self.width=width;self.pre=preprocessing
        self.seed=seed;rng=np.random.default_rng(seed)
        # Encoder output is tanh explicitly; response law takes no suffix input.
        self.context=MLP([xdim,width],rng)
        self.response=MLP([width,4+8*rdim+3],rng)
        self.candidate=MLP([width+adim,width,4],rng)

    @property
    def params(self):return self.context.params+self.response.params+self.candidate.params

    @property
    def parameter_count(self):return sum(p.size for p in self.params)

    def forward(self,x,a,r=None):
        xx,aa,rr=self.pre.transform(x,a,r) if self.pre else (finite(x),finite(a),None if r is None else finite(r))
        if xx.ndim!=2 or xx.shape[1]!=self.xdim or aa.ndim!=3 or aa.shape[0]!=len(xx) or aa.shape[2]!=self.adim:
            raise ValueError('Neural dimensions')
        zraw,ctx=self.context.forward(xx);z=np.tanh(zraw)
        raw,resp=self.response.forward(z);d=self.rdim
        pi=softmax(raw[:,:4]);mu=raw[:,4:4+4*d].reshape(-1,4,d)
        vunit=sigmoid(raw[:,4+4*d:4+8*d].reshape(-1,4,d));var=.01+3.99*vunit
        terminal=softmax(raw[:,-3:])
        joint=np.concatenate((np.broadcast_to(z[:,None,:],(len(z),aa.shape[1],self.width)),aa),-1)
        logits,cand=self.candidate.forward(joint.reshape(-1,self.width+self.adim))
        s=sigmoid(logits).reshape(len(z),aa.shape[1],4)
        lp=np.log(np.maximum(pi,1e-300))
        if rr is not None:
            if rr.shape!=(len(xx),d):raise ValueError('Residual shape')
            lp=lp-.5*(np.log(2*np.pi*var)+(rr[:,None,:]-mu)**2/var).sum(-1)
            w=softmax(lp)
        else:w=pi
        q=np.sum(w[:,None,:]*s,-1)
        output=dict(pi=pi,mu=mu,var=var,terminal=terminal,s=s,w=w,q=q,log_density=logsumexp(lp)[:,0])
        for value in output.values():finite(value)
        cache=(ctx,resp,cand,z,raw,vunit,rr,output)
        return output,cache

    def loss_and_grad(self,data):
        x,a,r=data['x'],data['a'],data['r'];terminal=data['terminal'];mask=data['mask']
        if not np.isin(terminal,[0,1,2]).all():raise ValueError('Terminal schema')
        active=terminal==2
        if np.any(mask[~active]) or np.any(mask.sum(1)[active]==0):raise ValueError('Terminal/active suffix labels')
        if not np.isin(data['y'][mask],[0,1]).all():raise ValueError('Binary branch labels required')
        # Duplicate action identities must already be canonicalized by collector.
        o,c=self.forward(x,a,r);ctx,resp,cand,z,raw,vu,rr,_=c
        weight=row_weights(data);cw=mask/np.maximum(mask.sum(1,keepdims=True),1)*weight[:,None]
        q=np.clip(o['q'],1e-12,1-1e-12);y=data['y']
        bce=float(np.sum(cw*(-y*np.log(q)-(1-y)*np.log1p(-q))))
        nll=float(-np.sum(weight*active*o['log_density'])/self.rdim)
        ce=float(-np.sum(weight*np.log(np.maximum(o['terminal'][np.arange(len(x)),terminal],1e-300))))
        dq=cw*(q-y)/(q*(1-q))
        ds=dq[:,:,None]*o['w'][:,None,:]*o['s']*(1-o['s'])
        dw=np.sum(dq[:,:,None]*o['s'],axis=1)
        dl=o['w']*(dw-np.sum(o['w']*dw,-1,keepdims=True))-o['w']*(weight*active/self.rdim)[:,None]
        dpi=dl-o['pi']*dl.sum(-1,keepdims=True)
        delta=rr[:,None,:]-o['mu']
        dmu=dl[:,:,None]*delta/o['var']
        dv=dl[:,:,None]*(-.5/o['var']+.5*delta**2/o['var']**2)*3.99*vu*(1-vu)
        dt=o['terminal'].copy();dt[np.arange(len(x)),terminal]-=1;dt*=weight[:,None]
        draw=np.concatenate((dpi,dmu.reshape(len(x),-1),dv.reshape(len(x),-1),dt),-1)
        dz1,gr=self.response.backward(draw,resp)
        dj,gc=self.candidate.backward(ds.reshape(-1,4),cand)
        dz2=dj[:,:self.width].reshape(len(x),a.shape[1],self.width).sum(1)
        _,gx=self.context.backward((dz1+dz2)*(1-z**2),ctx)
        grad=gx+gr+gc
        for value in grad:finite(value)
        return ce+nll+bce,grad,dict(terminal_ce=ce,response_nll=nll,outcome_bce=bce,
                                   source_count=len(set(data['source_ids'])),actual_response_terms=int(active.sum()))

    def save(self,path):
        p=Path(path)
        if p.exists():raise FileExistsError(p)
        meta=dict(kind='ACV0-artificial-or-reviewed-fit-only',xdim=self.xdim,adim=self.adim,rdim=self.rdim,
                  width=self.width,seed=self.seed,pre=self.pre is not None)
        payload={f'p{i}':v for i,v in enumerate(self.params)}
        if self.pre:
            for name in ('xmean','xstd','amean','astd','rmean','rstd'):payload[name]=getattr(self.pre,name)
            meta['fit_ids']=list(self.pre.fit_ids)
        payload['metadata']=np.array(json.dumps(meta))
        with p.open('xb') as f:np.savez(f,**payload)

    @classmethod
    def load(cls,path):
        # This loader is only for this explicitly typed small NumPy package.
        if Path(path).stat().st_size>20_000_000:raise ValueError('Checkpoint byte cap')
        with np.load(path,allow_pickle=False) as p:
            meta=json.loads(str(p['metadata']))
            if meta['kind']!='ACV0-artificial-or-reviewed-fit-only':raise ValueError('Checkpoint type')
            pre=Preprocessing(*(p[n].copy() for n in ('xmean','xstd','amean','astd','rmean','rstd')),meta['fit_ids']) if meta['pre'] else None
            model=cls(meta['xdim'],meta['adim'],meta['rdim'],meta['seed'],meta['width'],pre)
            for i,v in enumerate(model.params):
                if p[f'p{i}'].shape!=v.shape:raise ValueError('Checkpoint shape')
                v[:]=finite(p[f'p{i}'])
        return model


class OrdinaryModel:
    """Strong same-information MLP, no mixture. Inputs include actual post latent.

    x includes history, goal, clock, prefix and predicted-prefix latent. Candidate
    features include its actions and predicted terminal. The extra actual latent
    and residual are derived from exactly the same observed prefix as JointModel.
    """
    def __init__(self,xdim,adim,rdim,seed=94012,preprocessing=None):
        self.rdim=rdim;self.pre=preprocessing;self.seed=seed
        self.net=MLP([xdim+adim+2*rdim,64,64,1],np.random.default_rng(seed))

    @property
    def params(self):return self.net.params

    @property
    def parameter_count(self):return sum(p.size for p in self.params)

    def forward(self,x,a,r):
        # Last rdim coordinates of x are the predicted prefix latent by schema.
        actual=finite(x)[:,-self.rdim:]+finite(r)
        if self.pre:
            xx,aa,rr=self.pre.transform(x,a,r)
            actual=(actual-self.pre.xmean[-self.rdim:])/self.pre.xstd[-self.rdim:]
        else:xx,aa,rr=finite(x),finite(a),finite(r)
        n,k,_=aa.shape
        full=np.concatenate((np.broadcast_to(xx[:,None,:],(n,k,xx.shape[-1])),aa,
                             np.broadcast_to(actual[:,None,:],(n,k,self.rdim)),
                             np.broadcast_to(rr[:,None,:],(n,k,self.rdim))),-1)
        logits,cache=self.net.forward(full.reshape(n*k,-1))
        return sigmoid(logits).reshape(n,k),cache

    def loss_and_grad(self,data):
        q,cache=self.forward(data['x'],data['a'],data['r'])
        q=np.clip(q,1e-12,1-1e-12);mask=data['mask'];y=data['y']
        w=row_weights(data)[:,None]*mask/np.maximum(mask.sum(1,keepdims=True),1)
        loss=float(np.sum(w*(-y*np.log(q)-(1-y)*np.log1p(-q))))
        _,g=self.net.backward((w*(q-y)).reshape(-1,1),cache)
        return loss,g,dict(outcome_bce=loss)


class Adam:
    def __init__(self,params):
        self.params=params;self.m=[np.zeros_like(v) for v in params];self.v=[np.zeros_like(v) for v in params];self.t=0

    def step(self,grads):
        norm=np.sqrt(sum(float(np.sum(g*g)) for g in grads))
        if not np.isfinite(norm):raise ValueError('Nonfinite gradient')
        scale=min(1,5/max(norm,1e-300));self.t+=1
        for p,m,v,g in zip(self.params,self.m,self.v,grads):
            g=g*scale;m*=.9;m+=.1*g;v*=.999;v+=.001*g*g
            p-=.001*(m/(1-.9**self.t))/(np.sqrt(v/(1-.999**self.t))+1e-8)
            finite(p)


def train(model,data,epochs=12,batch_sources=64,seed=94013):
    if set(data['roles'])!={'fit'}:raise ValueError('Fitting role only')
    if epochs!=12 or batch_sources!=64:raise ValueError('No runtime update-budget sweep')
    rng=np.random.default_rng(seed);sources=np.unique(data['source_ids']);opt=Adam(model.params);trace=[]
    for epoch in range(epochs):
        order=rng.permutation(sources);losses=[]
        for start in range(0,len(order),batch_sources):
            keep=np.isin(data['source_ids'],order[start:start+batch_sources])
            batch={k:np.asarray(v)[keep] for k,v in data.items()}
            loss,g,_=model.loss_and_grad(batch);opt.step(g);losses.append(loss)
        trace.append(dict(epoch=epoch+1,loss=float(np.mean(losses))))
    return dict(trace=trace,updates=opt.t,parameters=model.parameter_count,seed=model.seed)
