"""Finite child/phase orchestration for a separately authenticated CPU caller.

No sbatch, main or stage/publication/SSD authority. This connects the tested
V2 child cleanup with the tested V2 schedule and private writer/validator roles.
The actual frozen caller must authenticate ALL stage/runtime/root/storage/CPU/
publication/SSD and exact Slurm dispatch gates BEFORE calling. A successful
source-only test of this library cannot replace any of those missing gates.
"""
import hashlib,os,time
from pathlib import Path
from wm_diag0_rc1_final_v1.cpu_process_v2 import run_child
from .archive_v2 import canonical,check_time
from .archive_pipeline_v1 import write_bounded
from .cpu_schedule_v2 import PhaseClock,prospective_analysis_argv,prospective_cpu_environment
from .cpu_entry_guard_v1 import authenticate_inputs
from .preservation_layout_v1 import check_paths
from .evidence_auth_v1 import ordinary,bound_json,bound_bytes
from wm_diag0_rc1_final_v1.postarchive_v1 import valid_identity

ROLES=('analysis','independent_acceptance','archive')


def identity(path,limit,deadline):
    p=ordinary(path);n=p.stat().st_size
    if n>limit:raise ValueError('finite closed technical control/log bytes')
    h=hashlib.sha256();count=0
    with p.open('rb') as f:
        while True:
            check_time(deadline);raw=f.read(min(1048576,limit-count+1))
            if not raw:break
            count+=len(raw)
            if count>limit:raise ValueError('closed control/log grew')
            h.update(raw)
    want={'bytes':count,'sha256':h.hexdigest()};bound_bytes(p,want,limit,deadline);return want


def validate_commands(commands):
    if not isinstance(commands,dict) or set(commands)!=set(ROLES):raise ValueError('all three implemented child phases required')
    for role,argv in commands.items():
        if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and '\x00' not in x for x in argv):raise ValueError('reviewed argv list, never shell/artifact code')
    return commands


def run_sequence(began,phases,commands,env,logs,artifact_roots,control_root,
                 authenticate_entry,close_analysis,authenticate_archive):
    """Trusted in-process composition; callbacks never loaded from artifacts.

    No retry. Each child runs in an owned group with its OWN five-second cleanup
    inside its phase. Entry authentication consumes first-phase time; all future
    phase maxima/finalization remain reserved. Every log/receipt is exclusive.
    Archive input logs are closed before close_analysis and archive child launch.
    The actual stage gate/fixed argv/environment are the caller's responsibility.
    """
    validate_commands(commands)
    if set(logs)!=set(ROLES) or set(artifact_roots)!=set(ROLES):raise ValueError('explicit complete role logs/artifacts')
    if not all(callable(x) for x in (authenticate_entry,close_analysis,authenticate_archive)):
        raise ValueError('reviewed in-process authenticators, not boolean ready flags')
    root=ordinary(control_root)
    if not root.is_dir():raise ValueError('existing external CPU control root')
    outputs=[Path(logs[p]) for p in ROLES]+[root/('PHASE-'+p+'.json') for p in ROLES]+[root/'CPU-PHASES-COMPLETE.json']
    if len(set(map(str,outputs)))!=len(outputs) or any(p.exists() or p.is_symlink() for p in outputs):
        raise FileExistsError('all logs/receipts/partials absent BEFORE any launch; preserve existing')
    for p in outputs:ordinary(p.parent)
    clock=PhaseClock(began,phases);phase_bounds=clock.claim('analysis',time.monotonic())
    entry=authenticate_entry(phase_bounds['work_deadline'])
    if not isinstance(entry,dict):raise ValueError('identity-bearing technical preflight record required')
    results={};closed=None;archive_proof=None
    for role in ROLES:
        if role!='analysis':phase_bounds=clock.claim(role,time.monotonic())
        if role=='archive':
            # Both owned writer/validator groups have been cleaned and their
            # ordinary log handles closed by run_child before this callback.
            closed=close_analysis(phase_bounds['work_deadline'])
            if not isinstance(closed,dict):raise ValueError('closed complete-analysis identity record')
        result=run_child(commands[role],env,logs[role],artifact_roots[role],40000000,100000,
                         phase_bounds['work_deadline'],phase_bounds['cleanup_deadline'])
        # Post-child metadata work must fit this phase's own final bookkeeping
        # second (the child can consume its whole work/cleanup reservations).
        if role=='archive':archive_proof=authenticate_archive(phase_bounds['phase_end_including_bookkeeping'])
        results[role]=result
        write_bounded(root/('PHASE-'+role+'.json'),canonical({'role':role,'child':result,
            'bounds':phase_bounds,'automatic_retry':False}),8000,phase_bounds['phase_end_including_bookkeeping'])
        clock.finish(role,time.monotonic())
    last=clock.claim('finalize',time.monotonic())
    if not isinstance(archive_proof,dict):raise ValueError('independent archive receipt identity required')
    result={'status':'CPU_PHASE_SEQUENCE_COMPLETED_PENDING_TERMINAL_CPU_AND_FINAL_SSD',
        'entry_preflight':entry,'closed_analysis':closed,'archive_readback':archive_proof,
        'phases':results,'CPU_allocation_seconds_cap':3600,'conversion_reserve_used':0,
        'automatic_retry':False,'scientific_values_emitted':False,'final_gate_ready':False}
    write_bounded(root/'CPU-PHASES-COMPLETE.json',canonical(result),64000,last['work_deadline'])
    clock.finish('finalize',time.monotonic());clock.complete(time.monotonic());return result


def analysis_commands(c,layout,expected,work_deadlines):
    """Fixed implemented writer/second-validator argv, never artifact commands.

    The future final caller must run authenticate_inputs before the first writer.
    Archive command integration is intentionally NOT invented as a no-op here.
    """
    check_paths(layout);valid_identity(expected,1000000)
    return {p:prospective_analysis_argv(c,layout,expected['sha256'],p,work_deadlines[p])
            for p in ('analysis','independent_acceptance')}


def cpu_environment(parent,source):
    return prospective_cpu_environment(parent,source)


def input_preflight(contract,expected,layout,deadline):
    return authenticate_inputs(contract,expected,layout,deadline)
