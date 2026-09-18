"""Fixed final-checkpoint training. Entry is only through approved worker."""
import time
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
        total=error=0.;count=0
        vrng=torch.Generator(device=device).manual_seed(seed+200000)
        with torch.no_grad():
            for i in range(0,len(val_ids),32):
                guard();ix=val_ids[i:i+32];inputs,actions=batch(arrays,stats,ix,device)
                if family=='gmm': losses=gmm_nll(model(*inputs),actions)
                else: losses=velocity_loss(model,inputs,actions,
                    torch.randn(actions.shape,device=device,generator=vrng),
                    torch.randint(0,1000,(len(ix),),device=device,generator=vrng))
                # Memory-bounded per-context validation sampling, fixed K=300.
                for row in range(len(ix)):
                    bank=sample(model,tuple(x[row:row+1] for x in inputs),300,vrng)
                    error+=float((bank-actions[row:row+1,None]).square().mean((2,3)).min())
                total+=float(losses.sum());count+=len(ix)
        return dict(family=family,seed=seed,updates=completed,row_presentations=presentations,
                    validation=dict(rows=count,loss=total/count,best_of_300_action_mse=error/count),
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
