"""Ordinary parent uses unchanged original scientific run function."""
import json,os,sys
from pathlib import Path
from .common import identity,write_new,SETTINGS,setting,check_usage,gates,canonical

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];index=int(sys.argv[3]);s,ri=setting(index);task=root/'tasks'/('grid-'+str(index));cp=root/'source/GRID-CONTRACT.json';c=json.loads(cp.read_text())
    if identity(cp)['sha256']!=expected or not c['rc1_grid']['grid_authorized'] or c['gpu_stages_authorized']:raise ValueError('exact grid-only contract')
    gates(c)
    import torch
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0) not in c['allowed_gpu_names'] or os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('one exact GPU')
    for n,x in c['prior_members'].items():
        if identity(Path(c['prior_source'])/n)!=x:raise ValueError('pinned original model/source/config')
    for x in c['lewm'].values():
        if identity(x['path'])!={k:x[k] for k in ('bytes','sha256')}:raise ValueError('own LeWM artifact')
    name,backbone=SETTINGS[s]
    if backbone=='lewm':
        from wm_diag0_rc1_technical_v1.models import CountedLeWM
        adapter=CountedLeWM(name,backbone,root/'source',c)
    else:
        from wm_diag0_rc1_v1.models import PointwiseAdapter
        adapter=PointwiseAdapter(name,backbone,root/'source',c)
        if canonical(adapter.contract.__dict__)!=canonical(c['rc1_technical']['head_suppliers'][str(s)]['route']):raise ValueError('own pointwise route')
    from wm_diag0_native_v3.runtime import verify_imports
    from wm_diag0_numerical_v3.worker import tensor_versions
    verify_imports(c,root/'source');before=tensor_versions(adapter.model)
    from wm_diag0_rc1_technical_v1.suppliers import head
    from wm_diag0_campaign_v4.readout import load
    hd,hs=head(c,s);readout=load(adapter,hd,hs)
    p=root/'source/ROOT-PLAN.json'
    if identity(p)['sha256']!=c['root_plan_sha256']:raise ValueError('fixed root identities')
    row=next(r for r in json.loads(p.read_text())['roots'] if r['task']==name and r['root_index']==ri)
    sa=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(sa)!=c['source_acceptance']:raise ValueError('accepted fixed sources')
    sources=json.loads(sa.read_text());key=name+'-'+str(ri).zfill(3)
    from wm_diag0_campaign_v4.diagnostic import run
    with torch.inference_mode():out=run(adapter,row,Path(c['source_runs'][name])/'tasks'/key/'output',sources['source_seals'][key],readout,task/'output',task/'controls/SELECTION-EXTERNAL.json',False)
    usage=dict(adapter.actual,cost_api_calls=adapter.cost_api_calls);check_usage(index,usage)
    if adapter.predictor_calls!=usage['predictor_calls'] or adapter.encoded_frames!=usage['encoded_frames']:raise ValueError('actual/manual counts disagree')
    if tensor_versions(adapter.model)!=before:raise ValueError('frozen model state changed')
    verify_imports(c,root/'source')
    from .resources import parent
    physical=parent(task/'output')
    write_new(task/'controls/WORKER-SUCCESS.json',{'phase':'RC1_grid','index':index,'setting':s,'root_index':ri,'output_seal':out,'actual_usage':usage,'physical_resource_usage':physical,'readout_output_seal':hs,'scientific_values_emitted':False})
    print(json.dumps({'status':'FIXED_RC1_PARENT_SEALED','index':index,'output_seal':out,'actual_usage':usage}))

if __name__=='__main__':main()
