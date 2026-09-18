"""FP32 common refinement and pinned staged decoder arithmetic."""
import torch


def affine(x, source_mean, source_std, target_mean, target_std):
    shape=x.shape
    x=x.float().reshape(*shape[:-2],15,2)
    sm,ss,tm,ts=[torch.as_tensor(v,device=x.device,dtype=torch.float64)
                 for v in (source_mean,source_std,target_mean,target_std)]
    if any(v.shape!=(2,) or not torch.isfinite(v).all() for v in (sm,ss,tm,ts)) or (ss<=0).any() or (ts<=0).any():
        raise ValueError('Invalid affine statistics')
    x=(x.double()*ss).float();x=(x.double()+sm).float()
    x=(x.double()-tm).float();x=(x.double()/ts).float()
    return x.reshape(shape)


def project(x, mean, std):
    raw=affine(x,mean,std,[0,0],[1,1])
    projected=raw.clamp(-1,1)
    out=affine(projected,[0,0],[1,1],mean,std)
    # Round-trip FP32 boundaries can move one ULP outside the Box. Move only
    # those encoded endpoints inward until the unchanged decoder is feasible.
    for _ in range(4):
        delivered=affine(out,mean,std,[0,0],[1,1])
        bad=delivered.abs()>1
        if not bad.any(): break
        out=torch.where(bad,torch.nextafter(out,torch.zeros_like(out)),out)
    if (affine(out,mean,std,[0,0],[1,1]).abs()>1).any(): raise RuntimeError('Unrepresentable support')
    return out,dict(exceeded=int((raw.abs()>1).sum()),coordinates=raw.numel(),
                    boundary=int((projected.abs()==1).sum()))


@torch.no_grad()
def cem(bank, cost, *, generator, project_fn, rounds=30, elites=30, noises=None):
    bank=bank.float();b,k=bank.shape[:2];logs=[]
    if bank.shape!=(b,k,3,10) or not 2<=elites<=k or rounds<1: raise ValueError('CEM shape/budget')
    for r in range(rounds):
        if not torch.isfinite(bank).all(): raise RuntimeError('Nonfinite bank')
        bank,projection=project_fn(bank)
        if bank.dtype!=torch.float32 or not torch.isfinite(bank).all(): raise RuntimeError('Projection dtype/values')
        values=cost(bank).float()
        if values.shape!=(b,k) or not torch.isfinite(values).all(): raise RuntimeError('Cost shape/values')
        ix=torch.argsort(values,dim=1,stable=True)[:,:elites]
        selected=bank[torch.arange(b,device=bank.device)[:,None],ix]
        mean=selected.mean(1);std=selected.std(1,correction=1)
        logs.append(dict(round=r,candidates=k,dtype=str(bank.dtype),projection=projection,
            population_std_mean=bank.std(1,correction=1).mean().item(),elite_std_mean=std.mean().item(),
            minimum=values.min(1).values.cpu().tolist(),mean_cost=values.mean(1).cpu().tolist(),
            elite_indices=ix.cpu().tolist(),unique=[len(torch.unique(v.reshape(k,-1),dim=0)) for v in bank]))
        if r+1<rounds:
            noise=(torch.randn(bank.shape,device=bank.device,dtype=torch.float32,generator=generator)
                   if noises is None else noises[r].to(device=bank.device,dtype=torch.float32))
            if noise.shape!=bank.shape: raise ValueError('Supplied noise shape')
            bank=noise*std[:,None]+mean[:,None];bank[:,0]=mean
    # Mean of feasible FP32 coordinates is mathematically feasible; rounding
    # may require the same support operation, not a separate execution clip.
    final,final_projection=project_fn(mean[:,None])
    logs[-1]['final_mean_projection']=final_projection
    return final[:,0],logs
