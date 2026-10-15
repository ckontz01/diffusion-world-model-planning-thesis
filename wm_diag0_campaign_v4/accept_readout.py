"""Independent fixed-ridge equation checks; no refit or checkpoint forward."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .readout import load
from wm_diag0.core import FeatureContract
from wm_diag0_native_v3.store import load_array,authenticate

def accept(directory,expected,c,setting):
    from .common import SETTINGS
    task,backbone=SETTINGS[setting];root=Path(directory)
    authenticate(root,expected,140_000_000,{'mean.npy','scale.npy','weights.npy','intercept.npy','READOUT.json','fit-features.npy','fit-labels.npy','validation-features.npy','validation-labels.npy','dual.npy'})
    meta=json.loads((root/'READOUT.json').read_text())
    d=dict(meta['contract']);d['feature_shape']=tuple(d['feature_shape']);d['positions']=tuple(d['positions']);contract=FeatureContract(**d)
    wanted=c['lewm'][task]['sha256'] if backbone=='lewm' else c['prior_members']['artifacts/'+task+'.pth']['sha256']
    if contract.backbone!=backbone or contract.feature_shape!=((192,) if backbone=='lewm' else (196,384)) or contract.history_length!=1 or contract.positions!=(5,10,15,20,25) or contract.checkpoint_sha256!=wanted:raise ValueError('fixed readout route/layout')
    accepted=json.loads((Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json').read_text())
    if meta['source_seals']!=accepted['source_seals']:raise ValueError('accepted source identities')
    model=load(SimpleNamespace(contract=contract,task=task,backbone=backbone),root,expected)
    if meta['alpha']!=1. or meta['fit_frames']!=256 or meta['validation_frames']!=96 or meta['validation_used_for_tuning']:raise ValueError('fixed readout fit')
    plan=json.loads((Path(c['run'])/'source/ROOT-PLAN.json').read_text())
    fit_rows=[r for r in plan['roots'] if r['task']==task and r['role']=='readout_fit']
    val_rows=[r for r in plan['roots'] if r['task']==task and r['role']=='readout_validation']
    if tuple(meta['fit_parents'])!=tuple(r['root_id'] for r in fit_rows) or meta['frame_parent_ids']!=[r['root_id'] for r in fit_rows for _ in range(16)] or meta['validation_parent_ids']!=[r['root_id'] for r in val_rows for _ in range(8)]:raise ValueError('whole-root roles and exact frame counts')
    nout=6 if task=='pusht' else 2;shape=contract.feature_shape
    x=load_array(root/'fit-features.npy',(256,*shape),['<f4']).astype(np.float64).reshape(256,-1)
    y=load_array(root/'fit-labels.npy',(256,nout),['<f8'])
    vx=load_array(root/'validation-features.npy',(96,*shape),['<f4']).astype(np.float64).reshape(96,-1)
    vy=load_array(root/'validation-labels.npy',(96,nout),['<f8'])
    dual=load_array(root/'dual.npy',(256,nout),['<f8'])
    for rows,actual in ((fit_rows,y),(val_rows,vy)):
        saved=[]
        for row in rows:
            key=task+'-'+str(row['root_index']).zfill(3);source=Path(c['source_runs'][task])/'tasks'/key/'output'
            authenticate(source,meta['source_seals'][key],12_000_000)
            saved.append(load_array(source/'training/labels.npy',(16 if row['role']=='readout_fit' else 8,nout),['<f8']))
        if not np.array_equal(actual,np.concatenate(saved)):raise ValueError('native training-coordinate identity')
    mean=x.mean(0);std=x.std(0);scale=np.where(std<1e-6,1.,std);intercept=y.mean(0)
    if not np.array_equal(mean,model.mean) or not np.array_equal(scale,model.scale) or not np.array_equal(intercept,model.intercept):raise ValueError('fit-only standardization/intercept')
    z=(x-mean)/scale;k=z@z.T+256*np.eye(256)
    if not np.allclose(k@dual,y-intercept,rtol=1e-8,atol=1e-8) or not np.allclose(z.T@dual,model.weights,rtol=1e-11,atol=1e-11):raise ValueError('fixed mean-loss alpha1 ridge equations')
    pred=((vx-model.mean)/model.scale)@model.weights+model.intercept
    quality={'coordinate_mae':np.mean(abs(pred-vy),axis=0),'coordinate_rmse':np.sqrt(np.mean((pred-vy)**2,axis=0))}
    if any(not np.allclose(v,np.asarray(meta['quality'][name]),rtol=1e-12,atol=1e-12) for name,v in quality.items()):raise ValueError('held-out quality without refit')
    return {'accepted':True,'task':task,'backbone':backbone,'output_seal':expected,'fit_parent_count':16,'validation_parent_count':12,
            'fit_frames':256,'validation_frames':96,'independent_equation_check_no_refit':True,'model_forwards':0}
