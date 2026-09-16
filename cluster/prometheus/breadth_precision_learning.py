"""Future 18 CPU fits and same-subset analysis. Never invoked by preparation."""
import importlib.util
from pathlib import Path
import time
import numpy as np
import breadth_precision_contract as p
import candidate_value_contract as ct
from candidate_value_data import read_npz,write_npz

from breadth_precision_freeze import CONFIGS,METRICS_SHA,check_frozen


def helpers():
    path=Path(__file__).resolve().parents[2]/'analysis/cvl1-objective-capacity-20260915-v1/study.py'
    p.require(p.sha(path)==METRICS_SHA,'Accepted metric/selector implementation')
    spec=importlib.util.spec_from_file_location('fixed_cvl_metrics',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def table(banks,relative):
    from candidate_value_learning import row_weights
    xs=[];bs=[];ys=[];keys=[]
    for b in banks:
        p.require(b['y'].shape[0]==8 and b['y'].shape[1] in (2,4) and np.isin(b['y'],(0,1)).all(),'Draw grid')
        base=b['base'];p.require(b['ids'][base]==b['continuation_index'],'Continuation identity')
        for i,original in enumerate(b['ids']):
            if relative and i==base:continue
            for d in range(b['y'].shape[1]):
                xs.append(b['x'][i]);bs.append(b['x'][base])
                ys.append(b['y'][i,d]-b['y'][base,d] if relative else b['y'][i,d])
                keys.append((b['reference'],b['horizon'],b['anchor'],original,d))
    return np.asarray(xs,np.float32),np.asarray(bs,np.float32),np.asarray(ys,np.float32),row_weights(keys),keys


def update_batches(n,updates,seed):
    """Original permutation/minibatch rule, truncated at a FIXED update count."""
    import torch
    import candidate_value_learning as c
    p.require(n>0 and updates>0,'Positive fixed budget')
    gen=torch.Generator().manual_seed(c.seed('training-order',seed))
    used=0
    while used<updates:
        for indices in torch.randperm(n,generator=gen).split(256):
            yield indices;used+=1
            if used==updates:return


def fit(banks,objective,seed,mean,scale):
    import torch
    import candidate_value_learning as c
    from candidate_value_models import transform
    relative=objective=='relative';x,bx,y,w,keys=table(banks,relative)
    allowed=set(p.allocation()['original_train']+p.allocation()['extra_train'])
    p.require(set(k[0] for k in keys)<=allowed,'No evaluation-source fitting')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed);model=c.ValueModel()
    opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    tx,tb,ty,tw=map(torch.from_numpy,(transform(x,mean,scale),transform(bx,mean,scale),y,w))
    examples=0;updates=0;began=time.monotonic()
    for ids in update_batches(len(y),p.UPDATES[objective],seed):
        opt.zero_grad(set_to_none=True);pred=model(tx[ids])
        loss=(pred-model(tb[ids])-ty[ids]).square() if relative else torch.nn.functional.binary_cross_entropy_with_logits(pred,ty[ids],reduction='none')
        loss=(loss*tw[ids]*len(y)).mean()
        p.require(torch.isfinite(loss),'Nonfinite training loss; no fallback')
        loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        opt.step();examples+=len(ids);updates+=1
    p.require(updates==p.UPDATES[objective],'Matched update budget')
    p.require(all(v.device.type=='cpu' and torch.isfinite(v).all() for v in model.parameters()),'Finite CPU-only final model')
    return model.eval().requires_grad_(False),dict(rows=len(y),updates=updates,row_presentations=examples,
        zero_targets=int((y==0).sum()),positive_targets=int((y>0).sum()),negative_targets=int((y<0).sum()),
        wall_seconds=time.monotonic()-began,seed=seed,objective=objective,parameters=87681)


def evaluate(banks,models,mean,scale):
    s=helpers();rows=[];predictions=[]
    for b in banks:
        meta={k:b[k] for k in ('reference','horizon','anchor','slot')}
        scores={};settings={};dispersion={}
        for config,ensemble in models.items():
            values,score=s.scores(ensemble,config,b['x'],b['base'],mean,scale)
            scores[config]=score;settings[config]=(config.endswith('bce'),True)
            choices=[]
            for seed,q in zip(p.SEEDS,values):
                key=config+'_seed'+str(seed);scores[key]=q;settings[key]=settings[config]
                choices.append(s.choose(q,b['ids'],b['base']))
            dispersion[config]=dict(seed_winner_disagreement=float(len(set(choices))>1),seed_score_std=float(values.std(0).mean()))
        scores.update(continuation=b['continuation'],immediate=b['immediate'])
        settings.update(continuation=(False,False),immediate=(False,False))
        pred={**meta,'ids':b['ids'],'outcomes':b['y'].tolist(),'scores':{}}
        for name,q in scores.items():
            chosen,m=s.metrics(q,b,*settings[name]);m.update(dispersion.get(name,{}))
            rows.append({**meta,'model':name,'selected_original_index':b['ids'][chosen],'metrics':m})
            pred['scores'][name]=q.tolist()
        rows.append({**meta,'model':'uniform_sampled8','metrics':dict(selected_success=float(b['y'].mean()),
            effect=float(b['y'].mean()-b['y'][b['base']].mean()))})
        predictions.append(pred)
    return s.summary(rows),rows,predictions


def train(run,out,source_sha):
    from breadth_precision_data import datasets
    from candidate_value_models import save_weights
    data=datasets(run,'training',source_sha);out=Path(out)
    norm=read_npz(p.normalizer_path());mean,scale=norm['mean'],norm['scale']
    p.require(mean.shape==scale.shape==(619,) and np.isfinite(mean).all() and
              np.isfinite(scale).all() and (scale>0).all(),'Accepted normalizer dimensions')
    write_npz(out/'normalization.npz',mean=mean,scale=scale)
    ledger=[];all_models={};training={}
    for condition in ('A','B','C'):
        expected=set(p.allocation()['original_train']+(p.allocation()['extra_train'] if condition=='B' else []))
        p.require({b['reference'] for b in data[condition]}==expected,'Full condition source set')
        models={}
        for objective in ('bce','relative'):
            config=condition+'_'+objective;models[config]=[]
            for seed in p.SEEDS:
                model,receipt=fit(data[condition],objective,seed,mean,scale)
                save_weights(out/(config+'-'+str(seed)+'.npz'),model)
                models[config].append(model);ledger.append(dict(receipt,condition=condition))
        summary,rows,pred=evaluate(data[condition],models,mean,scale)
        training[condition]=summary
        ct.json_write(out/('TRAIN-'+condition+'.json'),dict(summary=summary,rows=rows,predictions=pred))
        all_models.update(models)
    p.require(len(ledger)==18 and sum(x['updates'] for x in ledger)==30240,'Exact fixed fitting grid')
    members={x.name:p.sha(x) for x in out.iterdir() if x.is_file()}
    ct.json_write(out/'PRE-EVALUATION-FREEZE.json',dict(members=members,configs=list(CONFIGS),seeds=list(p.SEEDS),
        fitted_models=18,updates=p.UPDATES,new_source_sha256=source_sha,evaluation_outcomes_opened=False,
        selection='no model selection; report all six fixed ensembles',recorded_historical_nominee='original_relative'))
    support={k:dict(sources=len({b['reference'] for b in rows}),available_banks=len(rows),
        sampled_index_rows=8*len(rows),outcome_records=sum(b['y'].size for b in rows)) for k,rows in data.items()}
    return dict(fits=ledger,training=training,condition_support=support,models_frozen=True,evaluation_outcomes_opened=False,
                original_decision='stop_no_ranking_promise',no_automatic_closed_loop=True)


def analyze(run,out,source_sha):
    from candidate_value_models import load_weights
    from breadth_precision_data import datasets
    freeze=check_frozen(run,source_sha)
    directory=Path(run)/'fit-0';norm=read_npz(directory/'normalization.npz')
    models={k:[load_weights(directory/(k+'-'+str(seed)+'.npz'),False) for seed in p.SEEDS] for k in CONFIGS}
    banks=datasets(run,'evaluation',source_sha)
    p.require({b['reference'] for b in banks}==set(p.allocation()['evaluation']) and
              {(b['reference'],b['horizon']) for b in banks}==
              {(r,h) for r in p.allocation()['evaluation'] for h in (75,150)},'Every evaluation source and horizon')
    result,rows,pred=evaluate(banks,models,norm['mean'],norm['scale'])
    result['primary_contrasts']={obj:{name:result['models'][left+'_'+obj]['means']['effect']-
        result['models'][right+'_'+obj]['means']['effect'] for name,left,right in
        [('breadth_B_minus_A','B','A'),('precision_C_minus_A','C','A'),('allocation_B_minus_C','B','C')]}
        for obj in ('bce','relative')}
    # Paired per-source contrasts, not separate/draw/seed sample counts.
    for ref in result['reference_rows']:
        ref['allocation_contrasts']={obj:{name:ref['models'][left+'_'+obj]['effect']-ref['models'][right+'_'+obj]['effect']
            for name,left,right in [('B_minus_A','B','A'),('C_minus_A','C','A'),('B_minus_C','B','C')]}
            for obj in ('bce','relative')}
    from candidate_value_learning import reference_interval
    result['paired_allocation_intervals']={obj:{name:reference_interval(
        [r['allocation_contrasts'][obj][name] for r in result['reference_rows']])
        for name in ('B_minus_A','C_minus_A','B_minus_C')} for obj in ('bce','relative')}
    ct.json_write(Path(out)/'BANK-ROWS.json',rows);ct.json_write(Path(out)/'PREDICTIONS.json',pred)
    accounting={}
    for kind in ('breadth','precision','evaluation'):
        receipts=[ct.json_read(Path(run)/('%s-%d'%(kind,j['index']))/'REPORT.json')
                  for j in p.grid() if j['kind']==kind]
        accounting[kind]=dict(jobs=len(receipts),sources=len({r['reference'] for r in receipts}),
            new_outcomes=sum(r['new_outcomes'] for r in receipts),
            primitive_steps=sum(r['primitive_steps'] for r in receipts),
            available_banks=sum(sum(b['available'] for b in r['banks']) for r in receipts),
            unavailable_banks=sum(sum(not b['available'] for b in r['banks']) for r in receipts),
            final_budget_banks=sum(sum(b['available'] and b['anchor']==2*r['horizon']-15 for b in r['banks']) for r in receipts))
    return dict(evaluation=result,pre_evaluation_freeze_sha256=p.sha(directory/'PRE-EVALUATION-FREEZE.json'),
        actual_collection_accounting=accounting,
        source_references=32,available_banks=len(banks),new_evaluation_outcomes=sum(b['y'].size for b in banks),
        final_budget_banks=sum(b['anchor']==2*b['horizon']-15 for b in banks),
        original_decision='stop_no_ranking_promise',historical_nominee='original_relative',no_model_selected=True,
        no_automatic_closed_loop=True,development_only=True)
