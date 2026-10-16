"""New compact observation, outside every executed frozen research closure."""
import ast,base64,hashlib,inspect,json,shlex,subprocess,sys
from .common import DOC,identity,write_new
from wm_diag0_rc1_grid_v1.common import RUN
from wm_diag0_rc1_grid_v1.observer import OBSERVE

GRID_HASH='da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b'

def compact_payload(o):
    """Only technical observations; original controls remain at their roots."""
    d=o['dispatch']
    if d['array_job_id']!='317180' or d['indices']!=124 or d['contract_sha256']!=GRID_HASH or d['automatic_retries']!=0:raise ValueError('exact already-dispatched fixed grid')
    rows=[x.split('|') for x in o['scheduler'].splitlines() if x.strip()]
    terminal={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
    found={};raw_seen=set();terminal_seconds=3383;live_seconds=0;completed=[];faults=[]
    for x in rows:
        if len(x)!=7 or x[0] in found or x[5]!='4' or not x[4].isdigit():raise ValueError('unique exact scheduler row')
        found[x[0]]=x;state=x[2].split()[0];seconds=int(x[4])
        if x[0].startswith('317180_['):
            if state!='PENDING' or seconds or x[6]!='None assigned':raise ValueError('only unallocated grouped pending rows')
            continue
        if not x[0].startswith('317180_') or not x[0][7:].isdigit() or not 0<=int(x[0][7:])<124:raise ValueError('no unexpected grid logical job')
        if x[6] in ('gpu09','gpu09.cluster'):
            if x[1] in raw_seen or not 0<=seconds<=3600:raise ValueError('unique bounded allocated raw ID')
            raw_seen.add(x[1])
            if state in terminal:terminal_seconds+=seconds
            else:live_seconds+=seconds
        elif state!='PENDING':raise ValueError('assigned node unavailable/ambiguous, not inferred failure')
        if state=='COMPLETED' and x[3]=='0:0':completed.append(int(x[0][7:]))
        elif state in terminal:faults.append({'index':int(x[0][7:]),'state':state,'exit':x[3]})
    accepted=[];pending=[]
    for i,z in o['tasks'].items():
        if not i.isdigit() or not 0<=int(i)<124:raise ValueError('exact task index')
        s=z.get('STARTED');rr=z.get('RESULT');aa=z.get('ACCEPTED')
        if s and (s['array_job_id']!='317180' or s['index']!=int(i) or s['contract']!=GRID_HASH):raise ValueError('started source/dispatch binding')
        if aa and rr:
            if rr['status']!='ACCEPTED' or not aa['accepted'] or aa['contract_sha256']!=GRID_HASH or rr['output_seal']!=aa['output_seal']:raise ValueError('independently accepted control chain')
            row=found.get('317180_'+i)
            if not row or rr['job_id']!=row[1] or not s or s['job_id']!=row[1]:raise ValueError('accepted raw-ID binding')
            accepted.append(int(i))
            if int(i) not in completed:pending.append(int(i))
        elif aa:pending.append(int(i))
        if rr and rr['status']=='FAILED':faults.append({'index':int(i),'state':'CONTROL_FAILED'})
    if len(accepted)!=o['accepted_grid_parents'] or len(accepted)<35 or terminal_seconds<10631:raise ValueError('accepted history or cumulative charges regressed')
    active=o['active_process_records']
    if len(active)>1:raise ValueError('serial GPU invariant')
    verified=all(x.get('node_verification',{}).get('PID_exists') is True and x.get('node_verification',{}).get('start_ticks_match') is True for x in active)
    terminal_count=sum(x[2].split()[0] in terminal for x in rows if not x[0].startswith('317180_['))
    future=terminal_seconds+(124-terminal_count)*3600
    if future>468000 or o['full_future_GPU_reservation']!=449783 or o['CPU_before_analysis']!=1436:raise ValueError('all-attempt/full-future resource limit')
    if o['quality_choices_outcomes_or_predictions_read'] is not False:raise ValueError('technical metadata only')
    state='TECHNICAL_FAULT_OR_STOP' if faults or o['STOP'] is not None else ('PROCESS_VERIFICATION_UNAVAILABLE' if not verified else 'TECHNICAL_OBSERVATION_NO_FAULT_DETECTED')
    record={'status':state,'dispatch':d,'scheduler':o['scheduler'],'queue':o['queue'],'queue_diagnostic':o['queue_diagnostic'],
            'accepted_grid_parents':len(accepted),'accepted_indices':sorted(accepted),'publication_finalization_pending':sorted(set(pending)),
            'active_process_records':active,'STOP_present':o['STOP'] is not None,
            'STOP_sha256':hashlib.sha256(json.dumps(o['STOP'],sort_keys=True).encode()).hexdigest() if o['STOP'] is not None else None,
            'faults':faults,'GPU_terminal_all_attempts_seconds':terminal_seconds,'GPU_live_elapsed_not_final_seconds':live_seconds,
            'GPU_full_remaining_maxima_plus_terminal':future,'GPU_original_frozen_full_future':449783,'GPU_cap':468000,
            'CPU_charged_before_final':1436,'CPU_full_future':6836,'technical_control_inventory_sha256':hashlib.sha256(json.dumps(o['tasks'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'technical_control_count':len(o['tasks']),'all_original_controls_and_partials_retained':True,
            'scientific_values_or_quality_or_aggregates_inspected':False,'research_jobs_or_controllers_changed':False,
            'final_gate_ready':False,'complete_grid_technical_terminal_candidate':len(accepted)==124 and len(completed)==124 and not faults and o['STOP'] is None}
    if len(json.dumps(record,sort_keys=True).encode())>15000:raise ValueError('compact observation pre-output byte bound')
    return record

def program():
    # Reuse the already-reviewed frozen observer's reads and scheduler guard;
    # only its final stdout is compacted. No executed source file is patched.
    prefix='import builtins,hashlib,json,pathlib,os,resource\n'
    prefix+="os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))\nlo,hi=resource.getrlimit(resource.RLIMIT_AS)\ncap=min([8589934592]+[x for x in (lo,hi) if x!=resource.RLIM_INFINITY])\nresource.setrlimit(resource.RLIMIT_AS,(cap,cap))\n"
    prefix+='GRID_HASH='+repr(GRID_HASH)+'\n'+inspect.getsource(compact_payload)
    prefix+="\ndef print(raw):\n builtins.print(json.dumps(compact_payload(json.loads(raw)),sort_keys=True))\n"
    prefix+="r0=pathlib.Path("+repr(RUN)+")\nif hashlib.sha256((r0/'source/GRID-CONTRACT.json').read_bytes()).hexdigest()!=GRID_HASH:raise ValueError('executed grid contract bytes')\n"
    source='RUN='+repr(RUN)+'\n'+prefix+OBSERVE
    ast.parse(source,feature_version=(3,6));return source

def transport_command(source):
    ast.parse(source,feature_version=(3,6))
    encoded=base64.b64encode(source.encode()).decode()
    remote='timeout --kill-after=1s 20s python3 -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    return ['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','25s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','prometheus',remote]

def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive observation label')
    dst=DOC/('OBSERVE-'+label+'.json')
    if dst.exists() or (DOC/('OBSERVE-'+label+'.started.json')).exists():raise FileExistsError('no repeated/ambiguous observation')
    pub=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if pub['status']!='COMPLETION_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED':raise ValueError('new reviewed/published/SSD source gate')
    from .common import ROOT
    for n,x in pub['working_source_members'].items():
        if identity(ROOT/n)!=x:raise ValueError('published/preserved observation or authority bytes changed')
    write_new(DOC/('OBSERVE-'+label+'.started.json'),{'dispatch':'317180','source_package':pub['whole'],'program_sha256':hashlib.sha256(program().encode()).hexdigest()})
    # Independently finite remote owned process group AND native caller. A
    # failed observation is not evidence of failed research and is never retried.
    p=subprocess.run(transport_command(program()),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=26)
    if p.returncode:raise RuntimeError('bounded observation unavailable, not inferred research failure: '+p.stderr.decode(errors='replace')[:1500])
    if len(p.stdout)>16000:raise ValueError('remote compact metadata byte cap')
    z=json.loads(p.stdout)
    write_new(dst,z,limit=16000);print(json.dumps(z,sort_keys=True))

if __name__=='__main__':main()
