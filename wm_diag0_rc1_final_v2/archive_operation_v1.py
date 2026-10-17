"""Concrete archive child adapter, disabled without new frozen CPU contract.

No Slurm submission/transfer or whole-stage/publication/SSD authority. The future
frozen supervisor must authenticate those and actual CPU dispatch/runtime/root/
source-CPU/preparation proof BEFORE any analysis allocation or child invocation.
This module connects actual input/closed-analysis guards to inventory_v3 and the
once-only pipeline; its CLI cannot consume the current grid contract as authority.
"""
import hashlib,json,os,sys
from pathlib import Path,PurePosixPath
from .archive_v2 import canonical,check_time
from .archive_pipeline_v1 import preserve_authenticated_roots
from .analysis_closure_v1 import authenticate_closed
from .cpu_entry_guard_v1 import authenticate_inputs
from .evidence_auth_v1 import bound_json,bound_bytes
from .preservation_layout_v1 import check_paths
from .inventory_v3 import plan
from .cpu_schedule_v2 import v1 as schedule
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity

LAYOUT_MEMBER='final_evidence/PRESERVATION-LAYOUT-001.json'
PRIOR_MEMBER='final_evidence/PRECOMPUTE-ROOTS.json'
PREPARATION_MEMBER='final_evidence/PREPARATION-COPIES.json'
PREPARATION_PRODUCER='wm_diag0_rc1_final_v2/preparation_binding_v1.py'
LAYOUT={'bytes':10618,'sha256':'0f64eb876a3f0007ae0188f4902d4d8a114548d62e0c1cef610af02d5ffc3243'}


def preparation_bytes(c,record):
    """Bound producer/receipt declaration; actual native measurement is upstream.

    The final contract must pin this exact staged evidence identity, produced by
    separately tested preparation_binding_v1. Neither its schema nor arithmetic
    alone authenticates actual original host copies. That producer/full stage
    gate remains required before allocation, not replaced by this consumer.
    """
    if not isinstance(record,dict) or set(record)!={'schema','producer_source','full_future_preparation_bytes','measurement_commitment'}:
        raise ValueError('exact source-bound preparation-copy evidence schema')
    if record['schema']!='WM-DIAG0-RC1-PREPARATION-COPIES-v1':raise ValueError('actual full-copy preparation evidence role')
    producer=c['staged_members'].get(PREPARATION_PRODUCER)
    valid_identity(producer,2000000)
    if canonical(record['producer_source'])!=canonical(producer):raise ValueError('reviewed staged preparation measurement producer identity')
    valid_identity(record['measurement_commitment'],20000000)
    n=record['full_future_preparation_bytes']
    if type(n) is not int or not 0<n<=5368709120:raise ValueError('finite nonboolean full-future preparation logical bytes')
    return n


def preserve_closed_inventory(c,contract,taskdir,closed,planned,binding,authority,prior,
                              archive,portable,proof,rescan,preparation_full_future_bytes,deadline):
    """Trusted CPU core; synthetic fixtures do not grant production authority."""
    valid_identity(contract,1000000);check_time(deadline)
    if binding['final_contract_sha256']!=contract['sha256']:raise ValueError('same externally frozen analysis/archive contract')
    authenticate_closed(c,contract,taskdir,closed,deadline)
    result=preserve_authenticated_roots(planned,binding,authority,prior,archive,portable,proof,
                                      rescan,preparation_full_future_bytes,deadline)
    # Close record is independent of archive's own original/root digest. Both
    # must remain valid after archive readback, without deserializing results.
    authenticate_closed(c,contract,taskdir,closed,deadline)
    raw=canonical(closed)
    return {'status':'CLOSED_COMPLETE_ANALYSIS_ONCE_ARCHIVE_ORIGINAL_READBACK_VERIFIED_PENDING_TERMINAL_CPU_AND_SSD',
        'whole':result['whole'],'manifest':result['manifest'],'portable_inventory':result['portable_inventory'],
        'analysis_output_seal':closed['analysis_output_seal'],
        'closed_analysis_canonical_commitment':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
        'logical_members':result['logical_members'],'archive_created_once':True,
        'originals_independently_reread':True,'scientific_values_deserialized':False,
        'native_preparation_copies_measured_by_this_consumer':False,
        'terminal_CPU_and_designated_SSD_verified':False,'parent_publication_authorized':False,'final_gate_ready':False}


def archive_argv(c,layout,contract,closed_identity,work_deadline):
    """Fixed real child argv, no task/tmp write binding inside archive inputs.

    Future supervisor computes closed_identity AFTER its V2 children are cleaned
    and writes ANALYSIS-CLOSED.json outside inputs. This dynamic identity cannot
    be a precomputed self-reference in the final contract.
    """
    check_paths(layout);valid_identity(contract,1000000);valid_identity(closed_identity,8000);schedule.moment(work_deadline)
    source=layout['final_run']+'/source';ops=layout['operational_root']
    cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',source]
    # SIF itself is explicitly readable as an archive input inside the container.
    # Whole final/analysis task remains RO, including its CLOSED input logs.
    for p in sorted(set(layout['root_paths'].values())|{layout['study_base'],source}):cmd+=['--bind',p+':'+p+':ro']
    cmd+=['--bind',ops+':'+ops+':rw','--bind',ops+'/cpu/tmp-archive:/tmp:rw',
        c['sif'],c['venv']+'/bin/python','-B','-m','wm_diag0_rc1_final_v2.archive_operation_v1',
        source+'/FINAL-CONTRACT.json',canonical(contract).decode(),canonical(closed_identity).decode(),str(work_deadline)]
    return cmd


def cpu_context(env):
    # A consistency guard, NOT independent scheduler/Slurm cgroup authentication.
    # Actual allocation/process-tree limits and dispatch are the frozen caller's gate.
    if os.name!='posix':raise PermissionError('actual archive child requires authenticated Linux CPU allocation')
    job=env.get('SLURM_JOB_ID','')
    if not isinstance(job,str) or not job.isdigit() or env.get('SLURM_CPUS_PER_TASK')!='4' or env.get('SLURM_MEM_PER_NODE')!='8192':
        raise PermissionError('exact fourCPU/8GiB Slurm CPU-stage environment required')
    if any(env.get(k) for k in ('SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID','SLURM_JOB_GPUS','SLURM_STEP_GPUS','CUDA_VISIBLE_DEVICES')):
        raise PermissionError('no array/GPU allocation or visible GPU in CPU archive child')


def execute(contract_path,expected,closed_identity,deadline):
    """Future source-published/frozen supervisor only; never an early grid call."""
    cpu_context(os.environ);check_time(deadline);valid_identity(expected,1000000);valid_identity(closed_identity,8000)
    cp=Path(contract_path);c=bound_json(cp,expected,1000000,deadline)
    f=c.get('rc1_final',{})
    if f.get('analysis_authorized') is not True or c.get('gpu_stages_authorized') is not False:raise PermissionError('new frozen final CPU contract, never grid/draft')
    members=c['staged_members']
    if canonical(members.get(LAYOUT_MEMBER))!=canonical(LAYOUT):raise ValueError('exact source-bound complete19+final layout')
    layout_receipt=bound_json(cp.parent/LAYOUT_MEMBER,LAYOUT,32000,deadline);layout=check_paths(layout_receipt['layout'])
    if cp!=Path(layout['final_run'])/'source/FINAL-CONTRACT.json':raise ValueError('one exact final source contract path')
    # Full staged source, all59 original usage files and all127 new STARTED
    # controls reauthenticated; no boolean independently-authenticated substitute.
    authenticate_inputs(cp,expected,layout,deadline)
    prior=bound_json(cp.parent/PRIOR_MEMBER,members[PRIOR_MEMBER],64000,deadline)
    prep=bound_json(cp.parent/PREPARATION_MEMBER,members[PREPARATION_MEMBER],64000,deadline)
    prep_bytes=preparation_bytes(c,prep)
    closed_path=Path(layout['cpu_control_root'])/'ANALYSIS-CLOSED.json'
    closed=bound_json(closed_path,closed_identity,8000,deadline)
    def fresh():
        external={n:p for n,p in layout['root_paths'].items() if not n.startswith('study/')}
        return plan(layout['study_base'],layout['approved_children_with_final'],external,layout['approved_inert_alias_literals'])
    inventory=fresh();ops=Path(layout['operational_root'])
    result=preserve_closed_inventory(c,expected,layout['analysis_task'],closed,inventory,
        {'root_paths':layout['root_paths'],'final_contract_sha256':expected['sha256']},LAYOUT['sha256'],prior,
        layout['archive_path'],ops/'archive/portable-inventory.json',ops/'archive/ARCHIVE-READBACK.json',
        fresh,prep_bytes,deadline)
    bound_bytes(cp,expected,1000000,deadline);bound_bytes(closed_path,closed_identity,8000,deadline)
    return result


def main():
    if len(sys.argv)!=5:raise ValueError('fixed contract path/identity/closed identity/deadline argv only')
    result=execute(sys.argv[1],json.loads(sys.argv[2]),json.loads(sys.argv[3]),float(sys.argv[4]))
    print(json.dumps(result,sort_keys=True,allow_nan=False))


if __name__=='__main__':main()
