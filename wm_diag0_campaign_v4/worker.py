"""Allocated frozen readout/diagnostic stages; never a preparation/model probe."""
import hashlib,json,os,sys
from pathlib import Path
from .common import SETTINGS,identity,write_new
from wm_diag0_native_v3.store import seal,authenticate

def main():
    contract=Path(sys.argv[1]);expected=sys.argv[2];phase=sys.argv[3];index=int(sys.argv[4]);taskdir=Path(sys.argv[5])
    if identity(contract)['sha256']!=expected:raise ValueError('campaign contract identity')
    c=json.loads(contract.read_text());source=contract.parent
    if not c['gpu_stages_authorized'] or phase not in ('readout','technical','grid'):raise ValueError('exact frozen stage')
    import torch
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0) not in c['allowed_gpu_names']:raise ValueError('one exact RTX6000 Ada')
    if os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('exact node')
    for name,row in c['prior_members'].items():
        p=Path(c['prior_source'])/name
        if identity(p)!=row:raise ValueError('authenticated original model/source/config input')
    for row in c['lewm'].values():
        if identity(row['path'])!={k:row[k] for k in ('bytes','sha256')}:raise ValueError('LeWM artifact')
    accepted_path=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(accepted_path)!=c['source_acceptance']:raise ValueError('independent source gate')
    accepted=json.loads(accepted_path.read_text())
    plan=json.loads((source/'ROOT-PLAN.json').read_text())
    if identity(source/'ROOT-PLAN.json')['sha256']!=c['root_plan_sha256']:raise ValueError('root bytes')
    if phase=='readout':setting=index;root_index=None
    elif phase=='technical':setting=index;root_index=0
    else:setting=index//31;root_index=1+index%31
    task,backbone=SETTINGS[setting]
    from .models import Adapter
    adapter=Adapter(task,backbone,source,c)
    from wm_diag0_native_v3.runtime import verify_imports
    runtime=verify_imports(c,source)
    write_new(taskdir/'controls/RUNTIME-AND-GPU.json',{'GPU':torch.cuda.get_device_name(0),'CUDA_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),
                    'torch':torch.__version__,'source_contract_sha256':expected,'runtime_files':runtime})
    out=taskdir/'output'
    if phase=='readout':
        from .readout import fit
        result=fit(adapter,[r for r in plan['roots'] if r['task']==task],Path(c['source_run'])/'tasks',accepted['source_seals'],out)
    else:
        readout_dir=Path(c['run'])/'tasks'/('readout-'+str(setting))/'output'
        readout_control=json.loads((readout_dir.parent/'controls/ACCEPTED.json').read_text())
        from .readout import load
        head=load(adapter,readout_dir,readout_control['output_seal'])
        row=next(r for r in plan['roots'] if r['task']==task and r['root_index']==root_index)
        key=task+'-'+str(root_index).zfill(3);source_dir=Path(c['source_run'])/'tasks'/key/'output'
        from .diagnostic import run
        result=run(adapter,row,source_dir,accepted['source_seals'][key],head,out,taskdir/'controls/SELECTION-EXTERNAL.json',phase=='technical')
    after=verify_imports(c,source)
    write_new(taskdir/'controls/WORKER-SUCCESS.json',{'status':'COMPLETED_PENDING_INDEPENDENT_ACCEPTANCE','output_seal':result,
                    'phase':phase,'index':index,'setting':setting,'root_index':root_index,'predictor_calls':adapter.predictor_calls,'encoded_frames':adapter.encoded_frames,
                    'runtime_files_checked_after':len(after),'GPU':torch.cuda.get_device_name(0)})
    print(json.dumps({'status':'NATIVE_STAGE_OUTPUT_SEALED','phase':phase,'index':index,'output_seal':result}))

if __name__=='__main__':main()
