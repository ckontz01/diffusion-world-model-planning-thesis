"""Fixed final-checkpoint training. Entry is only through approved worker."""
import time
import shutil
from pathlib import Path
import numpy as np
import torch
from local_goal_models import LocalProposer,gmm_nll,velocity_loss,sample
from lgp1_tensor import affine
from lgp1_data import load_cache
import lgp1_contract as c

def batch(arrays,stats,indices,device):
    take=lambda name:torch.as_tensor(np.array(arrays[name][indices]),device=device,dtype=torch.float32)
    state=take('lowdim')
    state=(state-torch.as_tensor(stats['lowdim_mean'],device=device))/torch.as_tensor(stats['lowdim_std'],device=device)
    action=affine(take('actions'),[0,0],[1,1],stats['action_mean'],stats['action_std'])
    return (take('history'),take('local'),take('far'),state,take('remaining')),action

def batches(ids,seed,batch_size=128):
    rng=np.random.default_rng(seed);pending=np.empty(0,dtype=np.int64)
    while True:
        while len(pending)<batch_size: pending=np.r_[pending,rng.permutation(ids)]
        yield pending[:batch_size];pending=pending[batch_size:]

def validate(model,arrays,stats,val_ids,family,seed,guard,device):
    total=error=0.;count=0
    vrng=torch.Generator(device=device).manual_seed(seed+200000)
    with torch.no_grad():
        for i in range(0,len(val_ids),32):
            guard();ix=val_ids[i:i+32];inputs,actions=batch(arrays,stats,ix,device)
            if family=='gmm': losses=gmm_nll(model(*inputs),actions)
            else: losses=velocity_loss(model,inputs,actions,
                torch.randn(actions.shape,device=device,generator=vrng),
                torch.randint(0,1000,(len(ix),),device=device,generator=vrng))
            for row in range(len(ix)):
                bank=sample(model,tuple(x[row:row+1] for x in inputs),300,vrng)
                error+=float((bank-actions[row:row+1,None]).square().mean((2,3)).min())
            total+=float(losses.sum());count+=len(ix)
    return dict(rows=count,loss=total/count,best_of_300_action_mse=error/count)

def validate_saved_final(cache,out,prior,expected_hash,expected_seal,guard,device='cuda'):
    """Exact final-weight reuse; no optimizer construction or update path."""
    prior=Path(prior);out=Path(out)
    c.require(c.sha(prior/'sha256.txt')==expected_seal,'Preserved fit seal identity')
    c.verify(prior)
    c.require(c.sha(prior/'model.pt')==expected_hash,'Preserved final model identity')
    final=c.read(prior/'FINAL-CHECKPOINT.json')
    c.require(final==dict(selection='fixed_final',sha256=expected_hash,updates=12000),'Fixed final selection')
    arrays,stats,rows=load_cache(cache)
    p=torch.load(prior/'model.pt',map_location='cpu',weights_only=True)
    c.require(p['family']=='gmm' and p['seed']==8301 and p['updates']==12000 and
              p['row_presentations']==1536000 and p['cache_seal']==c.sha(Path(cache)/'sha256.txt'),
              'Saved training identity/budget/cache')
    c.require(set(stats)==set(p['stats']),'Saved normalizer keys')
    for k in stats:np.testing.assert_array_equal(stats[k],p['stats'][k].numpy())
    model=LocalProposer('gmm',**p['config']).to(device)
    model.load_state_dict(p['model'],strict=True);model.eval().requires_grad_(False)
    for name in ('model.pt','FINAL-CHECKPOINT.json'):
        with (prior/name).open('rb') as src,(out/name).open('xb') as dest:shutil.copyfileobj(src,dest)
    c.require(c.sha(out/'model.pt')==expected_hash,'Copied final weights changed')
    c.write(out/'TRAINING-PROVENANCE.json',dict(prior=str(prior),prior_seal_sha256=expected_seal,
        model_sha256=expected_hash,completed_updates_reused=12000,optimizer_updates_this_allocation=0,
        row_presentations_this_allocation=0,validation_rng_restart='seed+200000; no completed validation sampling existed'))
    val_ids=np.array([i for i,r in enumerate(rows) if r['role']=='P1_val'])
    c.require(len(val_ids)>0,'Missing validation role')
    result=validate(model,arrays,stats,val_ids,'gmm',8301,guard,device)
    c.require(c.sha(out/'model.pt')==expected_hash,'Validation mutated saved model file')
    for k,v in model.state_dict().items():torch.testing.assert_close(v.cpu(),p['model'][k],rtol=0,atol=0)
    return dict(family='gmm',seed=8301,updates=12000,row_presentations=1536000,
        optimizer_updates_this_allocation=0,row_presentations_this_allocation=0,validation_only=True,
        validation=result,model_sha256=expected_hash,cache_seal=p['cache_seal'],selection='fixed_final')

def train(cache,out,family,seed,guard,*,updates=12000,width=512,depth=3,heads=8,device='cuda',synthetic=False):
    if not synthetic: c.require(updates==12000 and (width,depth,heads)==(512,3,8),'Frozen training settings')
    arrays,stats,rows=load_cache(cache)
    train_ids=np.array([i for i,r in enumerate(rows) if r['role']=='P1_train'])
    val_ids=np.array([i for i,r in enumerate(rows) if r['role']=='P1_val'])
    c.require(len(train_ids)>0 and len(val_ids)>0,'Missing roles')
    torch.manual_seed(seed)
    model=LocalProposer(family,width=width,depth=depth,heads=heads).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4)
    rng=torch.Generator(device=device).manual_seed(seed+100000)
    it=batches(train_ids,seed);began=time.monotonic();completed=0;presentations=0
    try:
        for step in range(updates):
            guard();ix=next(it);inputs,actions=batch(arrays,stats,ix,device)
            optimizer.zero_grad(set_to_none=True)
            if family=='gmm': losses=gmm_nll(model(*inputs),actions)
            else:
                noise=torch.randn(actions.shape,device=device,generator=rng)
                timestep=torch.randint(0,1000,(len(ix),),device=device,generator=rng)
                losses=velocity_loss(model,inputs,actions,noise,timestep)
            loss=losses.mean();c.require(torch.isfinite(loss).item(),'Nonfinite training objective')
            loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
            c.require(torch.isfinite(norm).item(),'Nonfinite gradient')
            optimizer.step();completed+=1;presentations+=len(ix)
            if step==255 and not synthetic:
                elapsed=time.monotonic()-began
                c.require(elapsed+1.5*elapsed/256*(updates-256)<13500,'Measured fit cannot finish within guard')
        model.eval()
        payload=dict(family=family,seed=seed,config=dict(width=width,depth=depth,heads=heads),
            model={k:v.cpu() for k,v in model.state_dict().items()},stats={k:torch.from_numpy(v) for k,v in stats.items()},
            updates=completed,row_presentations=presentations,cache_seal=c.sha(Path(cache)/'sha256.txt'))
        # Save fixed final model BEFORE diagnostic validation. No selector reads val loss.
        torch.save(payload,out/'model.pt')
        c.write(out/'FINAL-CHECKPOINT.json',dict(sha256=c.sha(out/'model.pt'),updates=completed,selection='fixed_final'))
        validation=validate(model,arrays,stats,val_ids,family,seed,guard,device)
        return dict(family=family,seed=seed,updates=completed,row_presentations=presentations,
                    optimizer_updates_this_allocation=completed,row_presentations_this_allocation=presentations,
                    validation=validation,
                    model_sha256=c.sha(out/'model.pt'),cache_seal=payload['cache_seal'],selection='fixed_final')
    except BaseException:
        # Evidence only, never used for automatic continuation. SIGKILL may
        # prevent this write; Slurm terminal accounting remains authoritative.
        torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),completed_updates=completed,
                        row_presentations=presentations,resume_authorized=False),out/'interrupted.pt')
        raise

def load_model(root,device='cuda'):
    c.verify(root)
    p=torch.load(Path(root)/'model.pt',map_location=device,weights_only=True)
    c.require(p['updates']==12000 and p['row_presentations']==1536000,'Incomplete model')
    model=LocalProposer(p['family'],**p['config']).to(device)
    model.load_state_dict(p['model'],strict=True);model.eval().requires_grad_(False)
    return model,{k:v.cpu().numpy() for k,v in p['stats'].items()}
