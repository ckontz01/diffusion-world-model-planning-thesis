"""Actual frozen-source, terminal, historical, runtime/root and CPU gates."""
import json,os,resource,subprocess,time
from pathlib import Path
from wm_diag0_rc1_final_v2.evidence_auth_v1 import bound_json,bound_bytes,authenticate_usage
from wm_diag0_rc1_final_v2.archive_v2 import canonical,check_time
from .entry_source import source_closure
from wm_diag0_rc1_final_v2.recovery_suppliers_v1 import authenticate_terminal
from wm_diag0_rc1_final_v2.inventory_v3 import plan
from wm_diag0_rc1_final_v2.root_binding_v1 import compare
from .parallel_binding import parallel_authenticate
from .authorization import authorization
from .schedule import CPU_V2
from .layout import check_paths

def authenticate_inputs(contract,expected,layout,deadline):
    contract=Path(contract);check_paths(layout);check_time(deadline)
    if contract!=Path(layout['final_run'])/'source/FINAL-CONTRACT.json':raise ValueError('exact new final source')
    c=bound_json(contract,expected,1000000,deadline);f=c['rc1_final']
    recovery=bound_json(Path(c['run'])/'source/GRID-CONTRACT.json',f['grid_contract'],200000,deadline)
    if set(c)!=set(recovery)|{'rc1_final'}:raise ValueError('only final extension to exact recovery contract')
    for key,value in recovery.items():
        if key!='staged_members' and canonical(c[key])!=canonical(value):raise ValueError('fixed scientific field changed '+key)
    for name,value in recovery['staged_members'].items():
        if c['staged_members'].get(name)!=value:raise ValueError('executed source changed')
    if c['staged_members'].get('wm_diag0_rc1_final_v1/cpu_process_v2.py')!=CPU_V2:raise ValueError('original8269B V2 cleanup')
    if any(type(f.get(k)) is not int or f[k]!=v for k,v in {'allocation_seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0}.items()) or f.get('automatic_retry') is not False:raise ValueError('exact CPU-only resources')
    authorization(c,expected['sha256'],contract,layout['analysis_task'])
    closure=source_closure(contract.parent,c['staged_members'],deadline,'FINAL-CONTRACT.json')
    history=authenticate_usage(f['historical_usage_receipt']['path'],f['historical_usage_receipt']['identity'],deadline)
    terminal=authenticate_terminal(c,Path(layout['analysis_task'])/'controls/ALL-ALLOCATIONS-TERMINAL.json',f['all_allocations_terminal'],deadline)
    prior=bound_json(contract.parent/'final_evidence/PRECOMPUTE-ROOTS.json',c['staged_members']['final_evidence/PRECOMPUTE-ROOTS.json'],64000,deadline)
    external={k:v for k,v in layout['root_paths'].items() if not k.startswith('study/')}
    inventory=plan(layout['study_base'],layout['approved_children_with_final'],external,layout['approved_inert_alias_literals'])
    # Exclude ONLY the explicitly owned, not-yet-closed final root for comparison
    # to precompute commitments. Archive later binds that complete root too.
    label='study/'+Path(layout['final_run']).name
    members={n:r for n,r in inventory['members'].items() if not (n==label or n.startswith(label+'/'))}
    original=dict(inventory,members=members,root_labels=[n for n in inventory['root_labels'] if n!=label])
    total=sum(r['bytes'] for r in members.values() if r['type']=='file');original.update(logical_payload_bytes_no_discounts=total,archive_reserved_bytes=total+500000000)
    paths={k:v for k,v in layout['root_paths'].items() if k!=label}
    actual,_,_=parallel_authenticate(original,paths,prior['source_authority_sha256'],deadline);compare(actual,prior)
    bound_bytes(contract,expected,1000000,deadline)
    return {'status':'EXACT_FROZEN_SOURCE_139_TERMINAL_128_STARTS_HISTORY_FULL_RUNTIME_AND_ROOTS_AUTHENTICATED',
            'source_closure':closure,'history':history,'terminal':terminal,'original_whole_roots':len(paths),'scientific_payloads_read':False}

def allocation_gate(c,dispatch,deadline):
    check_time(deadline)
    job=os.environ.get('SLURM_JOB_ID','')
    if job!=dispatch['job_id'] or not job.isdigit() or os.environ.get('SLURM_CPUS_PER_TASK')!='4' or os.environ.get('SLURM_MEM_PER_NODE')!='8192':raise PermissionError('exact externally dispatched fourCPU/8GiB job')
    if any(os.environ.get(k) for k in ('SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID','SLURM_JOB_GPUS','SLURM_STEP_GPUS','CUDA_VISIBLE_DEVICES')):raise PermissionError('no GPU or array')
    result=subprocess.check_output(['scontrol','show','job','-o',job],universal_newlines=True,timeout=8,env=dict(os.environ,TZ='UTC'))
    fields=dict(x.split('=',1) for x in result.split() if '=' in x)
    if fields.get('JobState')!='RUNNING' or fields.get('NumCPUs')!='4' or fields.get('NumTasks')!='1' or fields.get('TimeLimit')!='01:00:00' or fields.get('Partition')!='defq':raise PermissionError('independent actual CPU scheduler allocation')
    if 'gpu' in fields.get('TresPerNode','').lower() or 'gres/gpu' in fields.get('AllocTRES','').lower():raise PermissionError('CPU allocation cannot contain GPU')
    affinity=os.sched_getaffinity(0)
    if not 0<len(affinity)<=4:raise PermissionError('native process-tree CPU placement')
    # Validate actual kernel memory enforcement, not an environment ready flag.
    limits=[];paths=[]
    for line in Path('/proc/self/cgroup').read_text().splitlines():
        _,controllers,path=line.split(':',2)
        if 'memory' in controllers.split(','):paths.append(Path('/sys/fs/cgroup/memory')/path.lstrip('/')/'memory.limit_in_bytes')
        if not controllers:paths.append(Path('/sys/fs/cgroup')/path.lstrip('/')/'memory.max')
    for path in paths:
        if path.is_file():
            raw=path.read_text().strip()
            if raw.isdigit():limits.append(int(raw))
    if not any(0<n<=8589934592 for n in limits):raise PermissionError('actual allocation-wide 8GiB kernel process-tree gate absent')
    lo,hi=resource.getrlimit(resource.RLIMIT_AS);cap=min([8589934592]+[x for x in (lo,hi) if x!=resource.RLIM_INFINITY]);resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    import calendar
    started=calendar.timegm(time.strptime(fields['StartTime'],'%Y-%m-%dT%H:%M:%S'))
    return {'job_id':job,'allocation_started_epoch':started,'affinity':sorted(affinity),'kernel_memory_limits':limits,'scheduler_job_sha256':__import__('hashlib').sha256(result.encode()).hexdigest()}
