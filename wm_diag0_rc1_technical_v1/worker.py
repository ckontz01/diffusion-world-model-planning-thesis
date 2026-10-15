"""Exactly three included native settings, fixed scientific plan and counters."""
import json,os,sys
from pathlib import Path
from .common import identity,write_new,SETTINGS,check_usage

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];setting=int(sys.argv[3]);task=root/'tasks'/('technical-'+str(setting))
    cp=root/'source/TECHNICAL-CONTRACT.json';c=json.loads(cp.read_text())
    if identity(cp)['sha256']!=expected or setting not in (1,2,3) or not c['rc1_technical']['three_settings_authorized'] or c['gpu_stages_authorized']:raise ValueError('three-setting-only contract')
    import torch
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0) not in c['allowed_gpu_names'] or os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('exact GPU')
    for n,x in c['prior_members'].items():
        if identity(Path(c['prior_source'])/n)!=x:raise ValueError('pinned original inputs')
    for x in c['lewm'].values():
        if identity(x['path'])!={k:x[k] for k in ('bytes','sha256')}:raise ValueError('LeWM original object identity')
    name,backbone=SETTINGS[setting]
    if backbone=='lewm':
        from .models import CountedLeWM
        adapter=CountedLeWM(name,backbone,root/'source',c)
    else:
        from wm_diag0_rc1_v1.models import PointwiseAdapter
        adapter=PointwiseAdapter(name,backbone,root/'source',c)
        from wm_diag0_rc1_heads_v1.route import require
        from wm_diag0.core import FeatureContract
        d=dict(c['rc1_technical']['head_suppliers'][str(setting)]['route']);d['feature_shape']=tuple(d['feature_shape']);d['positions']=tuple(d['positions'])
        require(adapter.contract,FeatureContract(**d))
    from wm_diag0_native_v3.runtime import verify_imports
    from wm_diag0_numerical_v3.worker import tensor_versions
    verify_imports(c,root/'source');before=tensor_versions(adapter.model)
    from .suppliers import head
    from wm_diag0_campaign_v4.readout import load
    directory,s=head(c,setting);readout=load(adapter,directory,s)
    p=root/'source/ROOT-PLAN.json'
    if identity(p)['sha256']!=c['root_plan_sha256']:raise ValueError('fixed root plan')
    row=next(r for r in json.loads(p.read_text())['roots'] if r['task']==name and r['root_index']==0)
    sa=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(sa)!=c['source_acceptance']:raise ValueError('accepted sources')
    sources=json.loads(sa.read_text());key=name+'-000'
    from .diagnostic import run
    with torch.inference_mode():result=run(adapter,row,Path(c['source_runs'][name])/'tasks'/key/'output',sources['source_seals'][key],readout,task/'output',task/'controls/SELECTION-EXTERNAL.json',c,setting)
    usage=dict(adapter.actual,cost_api_calls=adapter.cost_api_calls);check_usage(setting,usage)
    if adapter.predictor_calls!=usage['predictor_calls'] or adapter.encoded_frames!=usage['encoded_frames']:raise ValueError('independent module/manual call agreement')
    if tensor_versions(adapter.model)!=before:raise ValueError('frozen model state mutated')
    verify_imports(c,root/'source')
    write_new(task/'controls/WORKER-SUCCESS.json',{'status':'SEALED_PENDING_INDEPENDENT_ACCEPTANCE','setting':setting,'output_seal':result,'actual_usage':usage,
        'phase':'RC1_technical','original_head_or_new_RC1_supplier_seal':s,'GPU':torch.cuda.get_device_name(0),'quality_or_outcomes_emitted':False})
    print(json.dumps({'status':'RC1_NATIVE_SETTING_SEALED','setting':setting,'output_seal':result,'actual_usage':usage}))

if __name__=='__main__':main()
