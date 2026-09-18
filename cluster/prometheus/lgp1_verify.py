"""Independent saved-artifact checks; no model/physics calls or training imports."""
from pathlib import Path
import numpy as np
import lgp1_contract as c

def cache(root,*,synthetic=False):
    rows=c.read(Path(root)/'ROWS.json')
    for role,count in [('P1_train',80000),('P1_val',8000)]:
        rr=[r for r in rows if r['role']==role]
        c.require(len(rr)==count if not synthetic else bool(rr),'Cache role count')
        c.require(len({(r['episode'],r['t'],r['delta']) for r in rr})==len(rr),'Duplicate supervised tuple')
        c.require(all(r['t']>=10 and r['delta'] in range(15,151,15) for r in rr),'Alignment metadata')
    c.require(not {r['episode'] for r in rows if r['role']=='P1_train'} &
                  {r['episode'] for r in rows if r['role']=='P1_val'},'Source leakage')
    n=len(rows)
    for key,shape in dict(history=(n,3,192),local=(n,1,192),far=(n,1,192),lowdim=(n,11),
                           actions=(n,3,10),remaining=(n,)).items():
        a=np.load(Path(root)/(key+'.npy'),mmap_mode='r',allow_pickle=False)
        c.require(a.shape==shape and a.dtype==np.float32 and np.isfinite(a).all(),'Cache array contract '+key)
    state=np.load(Path(root)/'lowdim.npy',allow_pickle=False)
    c.require(np.array_equal(state[:,7:],state[:,[0,1,5,6]]),'State/proprio duplication')
    action=np.load(Path(root)/'actions.npy',allow_pickle=False)
    mask=np.array([r['role']=='P1_train' for r in rows])
    with np.load(Path(root)/'normalization.npz',allow_pickle=False) as z:
        for key,x in [('lowdim',state[mask]),('action',action[mask].reshape(-1,2))]:
            np.testing.assert_array_equal(z[key+'_mean'],x.astype(np.float64).mean(0).astype(np.float32))
            np.testing.assert_array_equal(z[key+'_std'],x.astype(np.float64).std(0).clip(1e-6).astype(np.float32))
    far=np.load(Path(root)/'far.npy',mmap_mode='r');local=np.load(Path(root)/'local.npy',mmap_mode='r')
    final=np.array([r['delta']==15 for r in rows])
    c.require(np.array_equal(far[final],local[final]),'Final-stage target switch')
    return dict(passed=True,rows=n,normalization_recomputed=True,source_disjoint=True)

def task(root,spec):
    root=Path(root);c.verify(root)
    meta=c.read(root/'TECHNICAL.json')
    c.require(meta['task']==spec and meta['complete'] is True,'Task identity/completion')
    c.require(meta['gpu_used']==spec['gpu'],'GPU contract')
    if spec['kind']=='fit':
        c.require(meta['updates']==12000 and meta['row_presentations']==1536000,'Fit budget')
        final=c.read(root/'FINAL-CHECKPOINT.json')
        c.require(final['sha256']==c.sha(root/'model.pt') and final['updates']==12000,'Model identity')
    if spec['kind'] in ('technical','evaluation'):
        c.require(meta['episodes']==2 and meta['models_unchanged'],'Episode count/frozen modules')
    return meta

def episodes(root,spec,reference):
    rows=c.read(Path(root)/'REPORT.json')['rows']
    c.require(len(rows)==2 and {r['horizon'] for r in rows}=={75,150},'Episode horizons')
    for r in rows:
        c.require((r['reference'],r['family'],r['seed'])==(spec['reference'],spec['family'],spec['seed']),'Episode identity')
        c.require(0<r['steps']<=2*r['horizon'] and r['success'] in (0,1) and r['failure'] is None,'Episode validity')
        c.require([s['elapsed'] for s in r['stages']]==list(range(0,r['steps'],15)),'Replanning positions')
        c.require(all(len(s['rounds'])==30 and all(v['candidates']==300 for v in s['rounds']) for s in r['stages']),'Refinement budget')
        from lgp1_endpoint import verify_file
        verify_file(root,r,reference)
    return rows
