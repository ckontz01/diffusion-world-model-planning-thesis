"""Freeze exact existing sources; no seeds, models or source roots generated."""
import ast,json
from pathlib import Path
from .common import *
from wm_diag0_preflight_v1.common import SIF,SIF_HASH,VENV

def blobs():
    out={}
    for package in ('wm_diag0_native_v3','wm_diag0','wm_diag0_preflight_v1'):
        for p in sorted((ROOT/package).glob('*.py')): out[package+'/'+p.name]=p.read_bytes()
    base=ROOT/'docs/world-model-diagnostic-a2-20261004/source-audit/point-lewm/stable-worldmodel'
    for p in sorted((base/'stable_worldmodel').rglob('*.py')):
        out[str(p.relative_to(base)).replace('\\','/')]=p.read_bytes()
    out['ROOT-PLAN.json']=(ROOT/'docs/world-model-diagnostic-a2-20261004/ROOT-PLAN.json').read_bytes()
    return out

def main():
    data=blobs()
    if sum(map(len,data.values()))>5_000_000: raise ValueError('new source reservation')
    for name,b in data.items():
        if name.endswith('.py'): compile(b,name,'exec',dont_inherit=True)
    if hashlib.sha256(data['ROOT-PLAN.json']).hexdigest()!=PLAN: raise ValueError('existing root bytes only')
    prior=json.loads((ROOT/'docs/world-model-diagnostic-a2-preflight-v1-20261015/stage-recovery-r1/CONTRACT.json').read_text())
    inv=json.loads((DOC/'RUNTIME-INVENTORY-001.json').read_text())
    render=json.loads((DOC/'RENDERER-R6-TEST-001.json').read_text())
    check=json.loads(render['stdout']) if not render['returncode'] else {}
    if render['returncode'] or check.get('status')!='ARTIFICIAL_SOFTWARE_RENDER_PASSED': raise RuntimeError('CPU software renderer gate')
    renderer=json.loads((DOC/'RENDERER-R5-MANIFEST.json').read_text())
    c={'study':'WM-DIAG0-A2','run':RUN,'source_generation_authorized':True,'gpu_stage_authorized':False,
       'full_campaign_ready':False,'native_implementation':'v3','root_plan_sha256':PLAN,
       'staged_members':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(data.items())},
       'runtime_manifest':inv['runtime_manifest'],'venv':VENV,'sif':SIF,'sif_sha256':SIF_HASH,
       'renderer':renderer,'renderer_path':RUN+'/renderer-r6','renderer_test':check,
       'prior_source':PRIOR+'/source','prior_members':prior['staged_members'],'lewm':prior['lewm'],
       'encoder_pin':'7764ea0f912e53c92e82eb78a2a1631e92725fc8',
       'source_attempts_max':120,'source_allocation_seconds':60,'source_work_seconds':45,'source_preserve_seconds':15,
       'source_cpus':4,'source_memory_bytes':8*1024**3,'source_output_bytes':12_000_000,'source_log_bytes':100_000,
       'source_live_bytes_reserved':1_440_000_000,'no_requeue':True,'max_concurrency':1,'replacements':0,
       'cpu_charged_before':17,'cpu_full_future_reserved':12600,'cpu_cap':13800,'gpu_full_future_reserved':468000,
       'conversion_1800_seconds':'unconsumed_unreassigned','live_full_future_bytes':12836395242,
       'live_cap':13000000000,'archive_cap':14000000000,'inclusive_cap':44000000000,
       'stop_on_technical_or_missing_window':True,'native_replay_tranche':'two additional fresh reset+20-action replays in each first-setting diagnostic allocation; no extra physics grants',
       'remaining_native_gates':['independent full-window authentication','four readouts','first four native diagnostic parity jobs','remaining fixed grid','independent analysis and full SSD verification']}
    write_new(DOC/'CONTRACT.json',c)
    print(json.dumps({'source_members':len(data),'source_bytes':sum(map(len,data.values())),'contract':identity(DOC/'CONTRACT.json'),
                      'root_plan_sha256':PLAN,'source_attempts':120,'gpu_authorized':False}))

if __name__=='__main__': main()
