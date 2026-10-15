"""Fixed fit-only float64 ridge; native input roles enforced before loading."""
import json
from pathlib import Path
import numpy as np
from wm_diag0_native_v3.store import load_array,save_array,seal,authenticate
from .common import identity,write_new
from wm_diag0.readout import Ridge,check_roles,realized_quality
from wm_diag0.core import frozen

def fit(adapter,roots,source_dir,source_seals,output):
    output=Path(output); output.mkdir(exist_ok=False)
    roles=tuple(tuple(r['root_id'] for r in roots if r['role']==role) for role in ('readout_fit','readout_validation','diagnostic'))
    check_roles(*roles)
    if tuple(map(len,roles))!=(16,12,32): raise ValueError('fixed native root allocation')
    xs=[];ys=[];fit_ids=[];vx=[];vy=[];val_ids=[]
    for row in roots:
        if row['role']=='diagnostic': continue
        key=row['task']+'-'+str(row['root_index']).zfill(3); directory=Path(source_dir)/key/'output'
        authenticate(directory,source_seals[key],12_000_000)
        record=json.loads((directory/'record.json').read_text())
        if record['root']!=row or not record['available']: raise ValueError('source role/availability')
        count=16 if row['role']=='readout_fit' else 8
        rgb=load_array(directory/'training/pixels.npy',(count,224,224,3),['|u1'],3_000_000)
        y=load_array(directory/'training/labels.npy',(count,6 if row['task']=='pusht' else 2),['<f8'],100_000)
        x=np.concatenate([adapter.encode(rgb[i:i+8]) for i in range(0,count,8)])
        if row['role']=='readout_fit': xs.append(x);ys.append(y);fit_ids.extend([row['root_id']]*count)
        else: vx.append(x);vy.append(y);val_ids.extend([row['root_id']]*count)
    xf=np.concatenate(xs);vf=np.concatenate(vx)
    x=xf.astype(np.float64).reshape(256,-1); y=np.concatenate(ys).astype(np.float64)
    mean=x.mean(0); scale=x.std(0); scale=np.where(scale<1e-6,1.,scale)
    z=(x-mean)/scale; intercept=y.mean(0)
    dual=np.linalg.solve(z@z.T+256*np.eye(256),y-intercept); weights=z.T@dual
    model=Ridge(adapter.contract,adapter.task,frozen(mean),frozen(scale),frozen(weights),frozen(intercept),tuple(sorted(set(fit_ids))))
    for name,a in zip(('mean','scale','weights','intercept'),(mean,scale,weights,intercept)): save_array(output/(name+'.npy'),a)
    for name,a in (('fit-features',xf),('fit-labels',y),('validation-features',vf),('validation-labels',np.concatenate(vy)),('dual',dual)): save_array(output/(name+'.npy'),a)
    write_new(output/'READOUT.json',{'task':adapter.task,'backbone':adapter.backbone,'contract':adapter.contract.__dict__,
                                    'fit_parents':model.fit_parent_ids,'frame_parent_ids':fit_ids,'validation_parent_ids':val_ids,'identity':model.identity,'alpha':1.,'fit_frames':256,
                                    'validation_frames':96,'quality':realized_quality(model,np.concatenate(vx),np.concatenate(vy)),
                                    'source_seals':source_seals,'validation_used_for_tuning':False})
    return seal(output,139_000_000 if adapter.backbone=='dinowm_noprop' else 4_900_000)

def load(adapter,directory,expected):
    directory=Path(directory)
    authenticate(directory,expected,140_000_000,{'mean.npy','scale.npy','weights.npy','intercept.npy','READOUT.json','fit-features.npy','fit-labels.npy','validation-features.npy','validation-labels.npy','dual.npy'})
    row=json.loads((directory/'READOUT.json').read_text())
    if row['task']!=adapter.task or row['backbone']!=adapter.backbone: raise ValueError('own readout only')
    d=int(np.prod(adapter.contract.feature_shape)); n=6 if adapter.task=='pusht' else 2
    arrays=[load_array(directory/(k+'.npy'),shape,['<f8']) for k,shape in (('mean',(d,)),('scale',(d,)),('weights',(d,n)),('intercept',(n,)))]
    if np.any(arrays[1]<=0): raise ValueError('positive fit scale')
    model=Ridge(adapter.contract,adapter.task,*[frozen(x) for x in arrays],tuple(row['fit_parents']))
    if model.identity!=row['identity']: raise ValueError('readout identity')
    return model
