"""SI1: approved-future CPU-only saved-data comparison; no planner imports/calls."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import time
import numpy as np
import torch
from torch import nn
import candidate_value_contract as ct
import candidate_value_learning as c
import breadth_precision_contract as bp
from candidate_value_models import normalize_fit
from breadth_precision_data import unpack

VERSION='candidate-value-score-information-20260918'
DOC='docs/'+VERSION
ROOT=Path(__file__).resolve().parents[2]
LINEAGE_SHA='633be15376a195ee35ef33b72694638b20967ecb82be2658f1eb0367c9aee8c5'
SEEDS=(8201,8202,8203)
CONDITIONS=('control','scores')
UPDATES=1800
CAPS=dict(cpu_allocation_wall_seconds=7200,cpus=4,memory_bytes=8*1024**3,
          artifact_bytes=1000000000,fits=24,gpu_allocations=0)


def folds():
    a=bp.allocation();refs=a['original_train']+a['extra_train']
    order=sorted(refs,key=lambda r:(hashlib.sha256((VERSION+'|fold|'+str(r)).encode()).hexdigest(),r))
    assert len(set(order))==192
    return [sorted(order[i*48:(i+1)*48]) for i in range(4)]


def metrics_module():
    path=ROOT/'analysis/cvl1-objective-capacity-20260915-v1/study.py'
    assert ct.sha(path)=='d54f2826a82af210d4148486f4a465e247f63ac7a8b8df54aa57cac839d166c5'
    spec=importlib.util.spec_from_file_location('accepted_metrics',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def saved_banks():
    """Consume pinned reports/banks only; not raw reference payloads or trajectories."""
    lock=ROOT/DOC/'LINEAGE.json';assert ct.sha(lock)==LINEAGE_SHA
    result=[]
    for entry in ct.json_read(lock)['roots']:
        d=Path(entry['path'])
        assert ct.sha(d/'sha256.txt')==entry['seal_sha256']
        assert ct.sha(d/'REPORT.json')==entry['report_sha256']
        report=ct.json_read(d/'REPORT.json')
        assert (report['reference'],report['horizon'])==(entry['reference'],entry['horizon'])
        banks={}
        for name,digest in entry['banks'].items():
            path=d/name;assert ct.sha(path)==digest
            # np.load is lazy: do not decode unrelated saved images/actions/state members.
            with np.load(path,allow_pickle=False) as z:
                banks[int(name[5:-4])]={k:z[k].copy() for k in
                    ('x','immediate','continuation','continuation_index')}
        result.extend(unpack(report,banks,[0,1]))
    assert len(result)==1426 and sum(b['y'].size for b in result)==22816
    assert {b['reference'] for b in result}==set(sum(folds(),[]))
    assert {(b['reference'],b['horizon']) for b in result}=={(r,h) for r in sum(folds(),[]) for h in (75,150)}
    return result


def inputs(bank):
    """Raw saved nonnegative costs, not ranks or candidate identity. Lower is better."""
    x=np.asarray(bank['x'],np.float32)
    scores=-np.stack((bank['immediate'],bank['continuation']),axis=1).astype(np.float32)
    assert x.shape==(8,619) and scores.shape==(8,2)
    assert np.isfinite(x).all() and np.isfinite(scores).all()
    return np.concatenate((x,scores),axis=1)


def table(banks):
    x=[];y=[];keys=[]
    for b in banks:
        assert b['y'].shape==(8,2) and np.isin(b['y'],(0,1)).all()
        z=inputs(b)
        for i,index in enumerate(b['ids']):
            for draw in (0,1):
                x.append(z[i]);y.append(b['y'][i,draw])
                keys.append((b['reference'],b['horizon'],b['anchor'],index,draw))
    return np.asarray(x,np.float32),np.asarray(y,np.float32),c.row_weights(keys),keys


def preprocessing(banks,fitting_refs):
    assert {b['reference'] for b in banks}==set(fitting_refs)
    x,_,w,_=table(banks)
    return normalize_fit(x,w)


def transform(x,mean,scale,condition):
    assert condition in CONDITIONS and mean.shape==scale.shape==(621,)
    assert np.isfinite(mean).all() and np.isfinite(scale).all() and (scale>0).all()
    z=(np.asarray(x,np.float32)-mean)/scale
    assert z.ndim==2 and z.shape[1]==621 and np.isfinite(z).all()
    if condition=='control':z[:,619:]=0.
    return z


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(621,128),nn.ReLU(),nn.Linear(128,64),nn.ReLU(),nn.Linear(64,1))
    def forward(self,x):return self.net(x).squeeze(-1)


def batches(n,seed,updates=UPDATES):
    assert n>0 and updates>0
    g=torch.Generator().manual_seed(c.seed('training-order',seed));count=0
    while count<updates:
        for ids in torch.randperm(n,generator=g).split(256):
            yield ids;count+=1
            if count==updates:return


def fit(x,y,w,seed,check):
    """Only called after explicit source-bound execution approval, never by preparation."""
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed);model=Model()
    opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    tx,ty,tw=map(torch.from_numpy,(x,y,w));start=time.monotonic();presentations=0;steps=0
    for ids in batches(len(y),seed):
        check();assert time.monotonic()-start<180,'Per-fit 180s allocation; stop, no retry'
        opt.zero_grad(set_to_none=True)
        loss=nn.functional.binary_cross_entropy_with_logits(model(tx[ids]),ty[ids],reduction='none')
        loss=(loss*tw[ids]*len(y)).mean();assert torch.isfinite(loss)
        loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step()
        steps+=1;presentations+=len(ids)
    assert steps==UPDATES and all(p.device.type=='cpu' and torch.isfinite(p).all() for p in model.parameters())
    return model.eval().requires_grad_(False),dict(seed=seed,updates=steps,row_presentations=presentations,
        fitting_rows=len(y),wall_seconds=time.monotonic()-start,parameters=sum(p.numel() for p in model.parameters()))


def evaluate(banks,models,mean,scale,fold,metrics):
    rows=[];predictions=[]
    for b in banks:
        meta={k:b[k] for k in ('reference','horizon','anchor','slot')}
        choices={};probabilities={}
        for condition in CONDITIONS:
            z=torch.from_numpy(transform(inputs(b),mean,scale,condition))
            with torch.inference_mode():values=torch.stack([m(z).sigmoid() for m in models[condition]]).numpy()
            q=values.mean(0);assert np.isfinite(q).all()
            chosen,stats=metrics.metrics(q,b,True,True);choices[condition]=chosen;probabilities[condition]=q.tolist()
            rows.append(dict(meta,fold=fold,model=condition,selected_original_index=b['ids'][chosen],metrics=stats))
            predictions.append(dict(meta,fold=fold,condition=condition,probabilities=q.tolist(),
                individual_seed_probabilities=values.tolist(),indices=b['ids']))
        a,best=choices['control'],choices['scores'];delta=b['y'][best]-b['y'][a]
        rows.append(dict(meta,fold=fold,model='treatment_minus_control',metrics=dict(effect=float(delta.mean()),
            gain=float((delta>0).mean()),loss=float((delta<0).mean()),departure=float(a!=best))))
        for name in ('continuation','immediate'):
            chosen,stats=metrics.metrics(b[name],b,False,False)
            rows.append(dict(meta,fold=fold,model=name,selected_original_index=b['ids'][chosen],metrics=stats))
    return rows,predictions


class Artifacts:
    def __init__(self,path):self.path=Path(path);self.path.mkdir(exist_ok=False);self.bytes=0
    def put(self,name,data):
        assert self.bytes+len(data)<900000000,'Artifact cap leaves 100MB for package/logs'
        p=self.path/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
        self.bytes+=len(data)
    def json(self,name,obj):self.put(name,(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    def npz(self,name,**arrays):
        f=io.BytesIO();np.savez_compressed(f,**arrays);self.put(name,f.getvalue())


def authorize(approval):
    from package_score_information import FILES
    manifest=ROOT/'SI1-SOURCE-MANIFEST.sha256'
    a=ct.json_read(approval)
    assert a.get('execution_authorized') is True and a.get('study')==VERSION
    assert a.get('source_sha256')==ct.sha(manifest) and a.get('caps')==CAPS
    assert a.get('lineage_sha256')==LINEAGE_SHA and a.get('fits')==24
    seen=set()
    for line in manifest.read_text().splitlines():
        digest,name=line.split('  ',1);assert name not in seen;seen.add(name)
        assert ct.sha(ct.child(ROOT,name))==digest
    assert seen==set(FILES), 'Exact source closure required'
    assert ct.json_read(ROOT/DOC/'FOLDS.json')['held_out']==folds()
    assert ct.sha(ROOT/DOC/'LINEAGE.json')==LINEAGE_SHA
    return a


def run(approval,output):
    a=authorize(approval)  # Mandatory BEFORE reading numerical data or creating an optimizer.
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and os.environ.get('SLURM_JOB_ID')
    assert os.environ.get('SLURM_CPUS_PER_TASK')=='4'
    assert Path(output).resolve().parent==bp.ROOT/'experiments'/VERSION
    torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    start=time.monotonic();out=Artifacts(output)
    def timeout(*args):raise RuntimeError('SI1 wall ceiling; preserve partials; no retry')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(6600)
    def check():
        assert time.monotonic()-start<6600
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<CAPS['memory_bytes']
    try:
        banks=saved_banks();metrics=metrics_module();all_rows=[];ledger=[]
        out.json('APPROVAL.json',a);out.json('FOLDS.json',dict(held_out=folds()))
        for i,held in enumerate(folds()):
            fitting=sorted(set(sum(folds(),[]))-set(held))
            train=[b for b in banks if b['reference'] in fitting]
            test=[b for b in banks if b['reference'] in held]
            assert len(fitting)==144 and len(held)==48 and not set(fitting)&set(held)
            mean,scale=preprocessing(train,fitting)
            out.npz('fold-%d/normalization.npz'%i,mean=mean,scale=scale)
            x,y,w,keys=table(train);models={}
            for condition in CONDITIONS:
                models[condition]=[];z=transform(x,mean,scale,condition)
                for seed in SEEDS:
                    model,record=fit(z,y,w,seed,check);models[condition].append(model)
                    ledger.append(dict(record,fold=i,condition=condition,fitting_refs=fitting))
                    out.npz('fold-%d/%s-%d.npz'%(i,condition,seed),**{k:v.numpy() for k,v in model.state_dict().items()})
            # Complete both fixed ensembles before evaluating this fold. No selection.
            out.json('fold-%d/FREEZE.json'%i,dict(fits=ledger[-6:],held_out=held,validation_used_for_fitting=False))
            rows,pred=evaluate(test,models,mean,scale,i,metrics);all_rows.extend(rows)
            out.json('fold-%d/predictions.json'%i,pred)
        assert len(ledger)==24 and sum(x['updates'] for x in ledger)==43200
        result=metrics.summary(all_rows)
        assert len(result['reference_rows'])==192
        out.json('BANK-ROWS.json',all_rows)
        out.json('REPORT.json',dict(study=VERSION,development_only=True,models=result,fits=ledger,
            fold_summaries={str(i):metrics.summary([r for r in all_rows if r['fold']==i]) for i in range(4)},
            runtime=dict(torch=torch.__version__,numpy=np.__version__,threads=torch.get_num_threads(),gpu_used=False),
            no_model_selected=True,no_full_data_fits=True,no_bp1_evaluation_access=True,
            no_new_labels=True,historical_decisions_changed=False,wall_seconds=time.monotonic()-start,
            process_cpu_seconds=time.process_time(),maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            artifact_bytes_before_report=out.bytes,bootstrap_intervals_descriptive_only=True))
    except BaseException as exc:
        out.json('TECHNICAL-STOP.json',dict(type=type(exc).__name__,reason=str(exc),no_retry=True));raise
    finally:signal.alarm(0)
    ct.seal(out.path)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--approval',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();run(args.approval,args.output)
