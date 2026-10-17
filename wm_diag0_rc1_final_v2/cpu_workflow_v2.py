"""Fixed dynamic closed-analysis/archive composition; no main or submission.

The future frozen caller must independently authenticate actual complete stage,
runtime/root/storage/sourceCPU/publication/SSD and exact Slurm dispatch authority.
In-process authenticators are reviewed source, NEVER artifact commands or flags.
Tests of this library do not furnish those gates or authorize actual analysis.
V1 and its passing tests remain unchanged historical source-only preparation.
"""
import time
from pathlib import Path
from .archive_v2 import canonical,check_time
from .archive_pipeline_v1 import write_bounded
from .analysis_closure_v1 import close_after_owned_children
from .archive_operation_v1 import archive_argv
from .cpu_schedule_v2 import CPU_V2,PhaseClock,prospective_analysis_argv
from .cpu_workflow_v1 import identity
from .evidence_auth_v1 import ordinary,bound_bytes
from .preservation_layout_v1 import check_paths
from wm_diag0_rc1_final_v1.cpu_process_v2 import run_child
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity

ROLES=('analysis','independent_acceptance','archive')
ARCHIVE_PARENT_SECONDS=30


def contract_shape(c,layout,contract,phases):
    check_paths(layout);valid_identity(contract,1000000)
    f=c.get('rc1_final',{})
    if f.get('analysis_authorized') is not True or c.get('gpu_stages_authorized') is not False:
        raise PermissionError('future frozen CPU-only contract, not grid or draft')
    wanted={'allocation_seconds':3600,'CPUs':4,'RAM_bytes':8589934592,'GPU_requested':0}
    if any(type(f.get(k)) is not int or f[k]!=v for k,v in wanted.items()) or f.get('automatic_retry') is not False:
        raise ValueError('unchanged nonboolean CPU3600/fourCPU/8GiB/noGPU/noRetry')
    if canonical(f.get('phase_seconds'))!=canonical(phases) or canonical(c.get('staged_members',{}).get('wm_diag0_rc1_final_v1/cpu_process_v2.py'))!=canonical(CPU_V2):
        raise ValueError('same frozen phase reservations and exact original8269B V2 cleanup')
    if type(phases.get('archive')) is not int or phases['archive']<=ARCHIVE_PARENT_SECONDS+6:
        raise ValueError('archive reserves own cleanup/bookkeeping AND parent authentication inside its phase')


def fixed_paths(layout):
    task=Path(layout['analysis_task']);ops=Path(layout['operational_root']);controls=ordinary(layout['cpu_control_root'])
    if not controls.is_dir():raise ValueError('existing external CPU control root')
    logs={p:task/'logs'/(p+'.log') for p in ROLES[:2]};logs['archive']=ops/'cpu/archive.log'
    outputs=list(logs.values())+[controls/('PHASE-'+p+'.json') for p in ROLES]
    outputs += [controls/'ANALYSIS-CLOSED.json',controls/'CPU-PHASES-COMPLETE.json']
    outputs += [task/'controls/ACCEPTED.json',task/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json']
    outputs += [task/'output'/n for n in ('RESULTS.json','ACCEPTANCE.json','MEMBERS.json')]
    outputs += [Path(layout['archive_path']),ops/'archive/portable-inventory.json',ops/'archive/ARCHIVE-READBACK.json']
    if len(set(map(str,outputs)))!=len(outputs) or any(p.exists() or p.is_symlink() for p in outputs):
        raise FileExistsError('all fixed outputs/logs/controls/archive/partials absent BEFORE any child; no retry')
    for p in outputs:ordinary(p.parent)
    artifacts={p:[str(task/'output'),str(task/'tmp')] for p in ROLES[:2]}
    # Never sample the <=14GB archive using the <=40MB child artifact guard.
    # Archive writers/readback independently enforce their own hard format caps.
    artifacts['archive']=[str(ordinary(ops/'cpu/tmp-archive'))]
    return controls,logs,artifacts


def run_fixed_sequence(c,layout,contract,began,phases,env,authenticate_entry,authenticate_archive):
    """Trusted in-process source composition, no arbitrary command parameter.

    Builds each fixed command using its ACTUAL claimed phase deadline. Only after
    both V2 owned writer/validator groups/logs close, hashes the independent proof,
    authenticates complete opaque outputs, exclusively writes closed record and
    passes its externally computed identity to the implemented archive child.
    Thirty seconds for post-child parent authentication are reserved INSIDE the
    archive phase; they are not borrowed from final30 or conversion1800. Native
    process-tree resources and all actual stage gates remain the caller's duty.
    """
    contract_shape(c,layout,contract,phases)
    if not all(callable(x) for x in (authenticate_entry,authenticate_archive)):
        raise ValueError('reviewed in-process entry/readback authenticators, not ready flags')
    controls,logs,artifacts=fixed_paths(layout)
    clock=PhaseClock(began,phases);bounds=clock.claim('analysis',time.monotonic())
    entry=authenticate_entry(bounds['work_deadline'])
    if not isinstance(entry,dict):raise ValueError('complete externally authenticated entry evidence required')
    check_time(bounds['work_deadline']);results={};closed_id=None;readback=None
    for role in ROLES:
        if role!='analysis':bounds=clock.claim(role,time.monotonic())
        child_bounds=dict(bounds)
        if role=='archive':
            proof=identity(Path(layout['analysis_task'])/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json',16000,bounds['work_deadline'])
            closed=close_after_owned_children(c,contract,layout['analysis_task'],proof,bounds['work_deadline'])
            closed_id=write_bounded(controls/'ANALYSIS-CLOSED.json',canonical(closed),8000,bounds['work_deadline'])
            bound_bytes(controls/'ANALYSIS-CLOSED.json',closed_id,8000,bounds['work_deadline'])
            child_bounds['work_deadline']-=ARCHIVE_PARENT_SECONDS
            child_bounds['cleanup_deadline']-=ARCHIVE_PARENT_SECONDS
            argv=archive_argv(c,layout,contract,closed_id,child_bounds['work_deadline'])
        else:argv=prospective_analysis_argv(c,layout,contract['sha256'],role,bounds['work_deadline'])
        check_time(child_bounds['work_deadline'])
        result=run_child(argv,env,logs[role],artifacts[role],40000000,100000,
                         child_bounds['work_deadline'],child_bounds['cleanup_deadline'])
        if not isinstance(result,dict) or type(result.get('returncode')) is not int or result['returncode']!=0:
            raise ValueError('owned child must complete successfully; no automatic retry')
        if role=='archive':
            readback=authenticate_archive(bounds['phase_end_including_bookkeeping'])
            if not isinstance(readback,dict):raise ValueError('independent archive technical readback evidence required')
            bound_bytes(controls/'ANALYSIS-CLOSED.json',closed_id,8000,bounds['phase_end_including_bookkeeping'])
        results[role]=result
        write_bounded(controls/('PHASE-'+role+'.json'),canonical({'role':role,'child':result,'bounds':bounds,
            'child_work_and_cleanup_bounds':child_bounds,'automatic_retry':False}),10000,bounds['phase_end_including_bookkeeping'])
        clock.finish(role,time.monotonic())
    last=clock.claim('finalize',time.monotonic())
    result={'status':'FIXED_CPU_CHILD_SEQUENCE_CLOSED_ANALYSIS_ARCHIVE_HANDOFF_PENDING_TERMINAL_CPU_AND_FINAL_SSD',
        'entry':entry,'closed_analysis_identity':closed_id,'archive_readback':readback,'phases':results,
        'archive_parent_auth_seconds_reserved_inside_archive_phase':ARCHIVE_PARENT_SECONDS,
        'CPU_allocation_seconds_cap':3600,'conversion_reserve_used':0,'automatic_retry':False,
        'scientific_values_emitted':False,'parent_publication_authorized':False,'final_gate_ready':False}
    write_bounded(controls/'CPU-PHASES-COMPLETE.json',canonical(result),64000,last['work_deadline'])
    clock.finish('finalize',time.monotonic());clock.complete(time.monotonic());return result
