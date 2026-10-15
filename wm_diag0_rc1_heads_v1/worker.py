"""One allocated fixed-root pointwise head, with real module counters."""
import json,os,sys
from pathlib import Path
from .common import identity,write_new,USAGE

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];setting=int(sys.argv[3]);task=root/'tasks'/('readout-'+str(setting))
    cp=root/'source/HEADS-CONTRACT.json';c=json.loads(cp.read_text())
    if identity(cp)['sha256']!=expected or setting not in (1,3) or not c['rc1_heads']['exact_two_fits_authorized'] or c['gpu_stages_authorized']:
        raise ValueError('exact two-head-only contract; no campaign dispatch')
    import torch
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0) not in c['allowed_gpu_names'] or os.uname().nodename not in ('gpu09','gpu09.cluster'):
        raise ValueError('exact GPU binding')
    for n,x in c['prior_members'].items():
        if identity(Path(c['prior_source'])/n)!=x:raise ValueError('pinned model/config/source input')
    from wm_diag0_rc1_v1.models import PointwiseAdapter
    from wm_diag0_native_v3.runtime import verify_imports
    from wm_diag0_numerical_v3.worker import tensor_versions
    from .route import original,amend,require
    taskname='pusht' if setting==1 else 'reacher'
    adapter=PointwiseAdapter(taskname,'dinowm_noprop',root/'source',c)
    require(adapter.original_contract,original(c,setting));require(adapter.contract,amend(adapter.original_contract))
    runtime=verify_imports(c,root/'source');before=tensor_versions(adapter.model)
    sa=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(sa)!=c['source_acceptance']:raise ValueError('fixed accepted source gate')
    accepted=json.loads(sa.read_text());planpath=root/'source/ROOT-PLAN.json'
    if identity(planpath)['sha256']!=c['root_plan_sha256']:raise ValueError('unchanged root manifest')
    roots=[r for r in json.loads(planpath.read_text())['roots'] if r['task']==taskname]
    from wm_diag0_campaign_v4.readout import fit
    with torch.inference_mode():out=fit(adapter,roots,Path(c['source_runs'][taskname])/'tasks',accepted['source_seals'],task/'output')
    if adapter.actual!=USAGE or adapter.encoded_frames!=352 or adapter.predictor_calls or adapter.cost_api_calls:raise ValueError('exact fit-only 352 pointwise frames/calls')
    if tensor_versions(adapter.model)!=before:raise ValueError('frozen model changed')
    verify_imports(c,root/'source')
    write_new(task/'controls/WORKER-SUCCESS.json',{'status':'SEALED_PENDING_INDEPENDENT_ACCEPTANCE','phase':'RC1_readout','setting':setting,
        'output_seal':out,'actual_usage':adapter.actual,'predictor_bundle_loads':1,'restricted_encoder_loads':1,'fit_frames':256,'validation_frames':96,
        'runtime_files_checked':len(runtime),'route':adapter.contract.__dict__,'GPU':torch.cuda.get_device_name(0),
        'scientific_quality_or_predictions_emitted':False,'CEM_calls':0,'physics_resets':0,'controller_actions':0})
    print(json.dumps({'status':'RC1_FIXED_HEAD_SEALED','setting':setting,'output_seal':out,'actual_usage':adapter.actual}))

if __name__=='__main__':main()
