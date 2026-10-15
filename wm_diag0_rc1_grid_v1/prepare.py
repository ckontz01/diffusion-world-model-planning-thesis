"""Freeze124 parents ONLY after authenticated terminal acceptance of all4 gates."""
import hashlib,json,sys
from .common import *

def additions():return {'wm_diag0_rc1_grid_v1/'+p.name:p.read_bytes() for p in sorted((ROOT/'wm_diag0_rc1_grid_v1').glob('*.py'))}

def main():
    from pathlib import Path
    if (DOC/'GRID-CONTRACT.json').exists():raise FileExistsError('one freeze')
    name=sys.argv[1]
    if Path(name).name!=name or not name.startswith('OBSERVE-') or not name.endswith('.json'):raise ValueError('one explicit local technical receipt')
    td=ROOT/'docs/world-model-diagnostic-rc1-technical-v1-20261016';z=json.loads((td/name).read_text())
    rows=[x.split('|') for x in z['scheduler'].splitlines() if x]
    if z['queue'] or z['STOP'] is not None or len(rows)!=3 or {x[0] for x in rows}!={'317177_1','317177_2','317177_3'} or any(x[2]!='COMPLETED' or x[3]!='0:0' or x[5]!='4' or x[6] not in ('gpu09','gpu09.cluster') for x in rows):raise ValueError('all three exact new native allocations must be terminal accepted first')
    previous=td/'TECHNICAL-CONTRACT.json'
    if identity(previous)['sha256']!='101cd417d9a823a559a29d3813887ad17f721b450ce4f21d267b597e4ef788fd':raise ValueError('actual executed technical closure')
    c=json.loads(previous.read_text());suppliers={}
    for k in ('1','2','3'):
        t=z['tasks'][k]
        if t['RESULT']['status']!='ACCEPTED' or not t['ACCEPTED']['accepted'] or t['RESULT']['output_seal']!=t['ACCEPTED']['output_seal']:raise ValueError('actual independent native acceptance')
        suppliers[k]={'run':TECHNICAL_RUN,'output_seal':t['ACCEPTED']['output_seal'],'acceptance_identity':t['RESULT']['acceptance_identity']}
    old=c['recovery']['accepted_suppliers']['technical-0'];suppliers['0']={'run':OLD_RUN,'output_seal':old['output_seal'],'acceptance_identity':old['control']}
    gpu=331+sum(int(x[4]) for x in rows)
    if gpu+124*3600>468000:raise ValueError('full future failure-inclusive reservation')
    if json.loads((DOC/'ARTIFICIAL-LOCAL-001.json').read_text())['status']!='PASSED':raise ValueError('new grid fixtures')
    for n,b in additions().items():
        compile(b,n,'exec');c['staged_members'][n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    c.update(run=RUN,dino_source=RUN+'/source/dino',gpu_stages_authorized=False,full_campaign_ready=False)
    c['rc1_technical']['three_settings_authorized']=False
    c['rc1_grid']={'grid_authorized':True,'analysis_authorized':False,'indices':124,'technical_run':TECHNICAL_RUN,'technical_contract':identity(previous),
        'technical_suppliers':suppliers,'technical_terminal_observation':identity(td/name),'technical_array_job_id':'317177','GPU_charged_before':gpu,'CPU_charged_before':1436,
        'allocated_attempts_before':14,'remaining_grid_attempts':124,'all_attempts_full_future':138,'full_future_GPU_seconds':gpu+124*3600,'full_future_CPU_seconds':6836,
        'automatic_retries':0,'work_seconds':3540,'independent_acceptance_seconds':55,'finalize_seconds':5,'allocation_seconds_each':3600,
        'original_science_and_run_function_unchanged':True,'all_four_setting_acceptances_before_dispatch':True,'final_analysis_and_all_lineage_archive_require_separate_completed_implementation':True}
    if sum(x['bytes'] for x in c['staged_members'].values())>5000000:raise ValueError('source closure bound')
    write_new(DOC/'GRID-CONTRACT.json',c);print(json.dumps({'status':'FIXED124_GRID_CONTRACT_FROZEN_AFTER_ALL4_GATES','contract':identity(DOC/'GRID-CONTRACT.json'),'GPU_all_attempts':gpu,'full_future_GPU':gpu+124*3600}))

if __name__=='__main__':main()
