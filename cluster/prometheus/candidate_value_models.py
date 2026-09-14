"""Train-only evaluator preprocessing, fixed fits, serialization and prediction."""
from pathlib import Path
import numpy as np
import torch
import candidate_value_learning as c
import candidate_value_contract as ct
from candidate_value_data import training_table,write_npz,read_npz

CONTEXT=np.r_[np.arange(384),np.arange(576,583),np.arange(613,619)]


def normalize_fit(x,w):
    x=np.asarray(x,np.float64);w=np.asarray(w,np.float64);w=w/w.sum()
    mean=(x*w[:,None]).sum(0)
    scale=np.sqrt(((x-mean)**2*w[:,None]).sum(0))
    scale=np.where(scale<1e-6,1.,scale)
    return mean.astype(np.float32),scale.astype(np.float32)


def transform(x,mean,scale,context=False):
    y=(np.asarray(x,np.float32)-mean)/scale
    ct.require(y.shape[1:]==(619,) and np.isfinite(y).all(),'Evaluator preprocessing')
    if context:
        mask=np.zeros(619,bool);mask[CONTEXT]=True;y[:,~mask]=0
    return y


def save_weights(path,model):
    write_npz(path,**{k:v.detach().cpu().numpy() for k,v in model.state_dict().items()})


def load_weights(path,linear):
    with torch.random.fork_rng(devices=[]):model=c.ValueModel(linear)
    model.load_state_dict({k:torch.from_numpy(v) for k,v in read_npz(path).items()},strict=True)
    return model.eval().requires_grad_(False)


def train(run,out,source_sha,capsule_sha):
    x,y,keys=training_table(run,source_sha,capsule_sha)
    support=dict(rows=len(y),positive_labels=int(y.sum()),positive_references=len({k[0] for k,v in zip(keys,y) if v}))
    if not c.sparse_gate(keys,y):return dict(advance=False,decision='insufficient_success_support',support=support)
    w=c.row_weights(keys);mean,scale=normalize_fit(x,w)
    write_npz(Path(out)/'normalization.npz',mean=mean,scale=scale,minimum=x.min(0),maximum=x.max(0))
    z=transform(x,mean,scale);counts={}
    for number in ct.TRAIN_SEEDS:
        model=c.fit(z,y,keys,model_seed=number,epochs=40)
        save_weights(Path(out)/('value-%d.npz'%number),model)
        counts['value-%d'%number]=sum(p.numel() for p in model.parameters())
    for name,is_context in (('linear',False),('context',True)):
        z=transform(x,mean,scale,context=is_context)
        model=c.fit(z,y,keys,linear=True,model_seed=8201,epochs=40)
        save_weights(Path(out)/(name+'.npz'),model)
        counts[name]=sum(p.numel() for p in model.parameters())
    return dict(advance=True,decision='fixed_models_frozen',support=support,parameters=counts,
                constant_probability=float(np.sum(y*w)/w.sum()),training_seeds=list(ct.TRAIN_SEEDS),
                feature_fit_references=ct.allocation()['train'],epochs=40,context_dimension=len(CONTEXT),
                training_rows=len(keys),unique_candidate_rows=len(keys)//2,
                validation_or_closed_loop_used=False)


class Predictor:
    def __init__(self,run,source_sha,capsule_sha):
        p=Path(run)/'fit-0'
        self.report=ct.check_report(p,'fit',0,source_sha,capsule_sha)
        ct.require(self.report['advance'] is True and self.report['feature_fit_references']==ct.allocation()['train']
                   and self.report['training_seeds']==list(ct.TRAIN_SEEDS),'Training selection provenance')
        norm=read_npz(p/'normalization.npz');self.mean,self.scale=norm['mean'],norm['scale']
        self.minimum,self.maximum=norm['minimum'],norm['maximum']
        ct.require(self.mean.shape==self.scale.shape==(619,) and np.isfinite(self.mean).all()
                   and np.isfinite(self.scale).all() and (self.scale>0).all(),'Preprocessing coefficients')
        self.models={'value':[load_weights(p/('value-%d.npz'%n),False) for n in ct.TRAIN_SEEDS],
                     'linear':[load_weights(p/'linear.npz',True)],'context':[load_weights(p/'context.npz',True)]}

    def __call__(self,arm,x):
        return c.probabilities(self.models[arm],transform(x,self.mean,self.scale,context=arm=='context'))

    def diagnostics(self,x,p):
        return dict(feature_outside_training_range_fraction=float(np.mean((x<self.minimum)|(x>self.maximum))),
                    score_saturation_fraction=float(np.mean((p<=.01)|(p>=.99))),
                    score_minimum=float(p.min()),score_maximum=float(p.max()))
