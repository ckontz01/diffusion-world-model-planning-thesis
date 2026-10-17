"""Finite CPU phase reservations and prospective fixed read-only runtime argv.

NO main, sbatch, process launch or execution authorization. Actual entry/gate/
Slurm-dispatch/terminal-CPU integration remains separate. This file is preparation
only; an artificial phase split is not a whole-study timing guarantee.
"""
import math
from pathlib import PurePosixPath
from .archive_v2 import canonical
from .preservation_layout_v1 import check_paths,GRID
from .inventory_v3 import safe_name

PHASES=('analysis','independent_acceptance','archive','finalize')
CLEANUP_SECONDS=5
BOOKKEEPING_SECONDS=1
CPU_V2={'bytes':10254,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}


def phase_seconds(phases):
    if not isinstance(phases,dict) or set(phases)!=set(PHASES) or any(type(phases[p]) is not int or phases[p]<=CLEANUP_SECONDS+BOOKKEEPING_SECONDS for p in PHASES):
        raise ValueError('exact positive integer phase reservations including own cleanup/bookkeeping')
    if sum(phases.values())!=3600 or phases['finalize']<30:raise ValueError('all four phases including final receipts fit unchanged3600s')
    return phases


def validate_draft(grid,proposed,layout):
    check_paths(layout)
    if set(proposed)!=set(grid)|{'rc1_final'}:raise ValueError('only new explicit final metadata/source closure')
    for k,v in grid.items():
        if k!='staged_members' and canonical(proposed[k])!=canonical(v):raise ValueError('all fixed science/suppliers/resource/source fields unchanged')
    staged=proposed['staged_members']
    for n,want in grid['staged_members'].items():
        if staged.get(n)!=want:raise ValueError('never edit/replace an executed frozen source')
    for n in set(staged)-set(grid['staged_members']):
        safe_name(n)
        if not n.startswith(('wm_diag0_rc1_final_v1/','wm_diag0_rc1_final_v2/','final_evidence/')):raise ValueError('only new final source/evidence roles')
    cleanup=staged.get('wm_diag0_rc1_final_v1/cpu_process_v2.py',{})
    if cleanup.get('sha256')!=CPU_V2['sha256']:raise ValueError('tested V2 owned-group cleanup mandatory; defective V1 never production')
    f=proposed['rc1_final']
    if f.get('analysis_authorized') is not False:raise PermissionError('draft cannot grant actual analysis/allocation authority')
    resources=('allocation_seconds','CPUs','RAM_bytes','GPU_requested')
    if any(type(f.get(k)) is not int for k in resources) or type(f.get('automatic_retry')) is not bool:raise ValueError('nonboolean exact CPU resource integer fields')
    if tuple(f[k] for k in resources)+(f['automatic_retry'],)!=(3600,4,8589934592,0,False):raise ValueError('unchanged CPU3600/fourCPU/8GiB/noGPU/noRetry')
    if f.get('grid_run')!=grid['run'] or f.get('grid_contract')!=GRID or f.get('run')!=layout['final_run'] or f.get('operational_root')!=layout['operational_root'] or f.get('archive_path')!=layout['archive_path']:
        raise ValueError('same grid and disjoint complete final/preservation roots')
    phase_seconds(f['phase_seconds'])
    return {'status':'FIXED_SCIENCE_V2_CPU_RESOURCE_AND_PHASE_DRAFT_VALID_NOT_EXECUTION_AUTHORITY',
            'analysis_authorized':False,'CPU_full_future_seconds':6836,'conversion_reserved_seconds_untouched':1800,
            'phase_seconds':f['phase_seconds'],'cleanup_seconds_within_each_child_phase':CLEANUP_SECONDS,
            'bookkeeping_seconds_within_each_child_phase':BOOKKEEPING_SECONDS,
            'final_gate_ready':False,'actual_complete_supervisor_submission_or_stage_gates_passed':False}


def moment(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('finite nonboolean monotonic timestamp')
    return value


class PhaseClock:
    """One-use ordered phases. Earlier under-use does NOT extend a later phase.

    Entry/authentication time consumes the first phase. Every claim reserves ALL
    remaining phase maxima, including finalization, within the same allocation.
    No sleeps/retry/refunds or conversion-reserve borrowing are supplied here.
    """
    def __init__(self,began,phases):
        self.began=moment(began);self.end=self.began+3600;self.phases=dict(phase_seconds(phases));self.next=0;self.active=None
    def claim(self,name,now):
        now=moment(now)
        if self.active is not None or self.next>=len(PHASES) or name!=PHASES[self.next] or now<self.began:raise ValueError('ordered once-only phase claim')
        start=self.began if self.next==0 else now
        end=start+self.phases[name];future=sum(self.phases[p] for p in PHASES[self.next+1:])
        if now>=end-CLEANUP_SECONDS-BOOKKEEPING_SECONDS or end+future>self.end:raise TimeoutError('full future phase/final cleanup reservation cannot fit; stop affected work')
        bounds={'work_deadline':end-CLEANUP_SECONDS-BOOKKEEPING_SECONDS,
                'cleanup_deadline':end-BOOKKEEPING_SECONDS,'phase_end_including_bookkeeping':end,
                'remaining_future_phase_reservation_seconds':future,'allocation_end':self.end}
        self.active=(name,bounds);return dict(bounds)
    def finish(self,name,now):
        now=moment(now)
        if self.active is None or self.active[0]!=name or now>self.active[1]['phase_end_including_bookkeeping'] or now<self.began:
            raise TimeoutError('one phase exceeded its own bound; preserve partials, no time transfer')
        self.active=None;self.next+=1
    def complete(self,now):
        if self.active is not None or self.next!=len(PHASES) or moment(now)>self.end:raise ValueError('all four bounded phases and finalization required')
        return {'status':'ALL_PHASE_BOUNDS_MET_NOT_RESEARCH_ACCEPTANCE','elapsed_seconds':now-self.began,
                'allocation_seconds_cap':3600,'conversion_reserve_used':0,'automatic_retry':False,'final_gate_ready':False}


VALIDATE_CODE="""import json,sys
from pathlib import Path
from wm_diag0_rc1_final_v2.analysis_validate_v1 import validate_complete
from wm_diag0_rc1_grid_v1.common import write_new
proof=validate_complete(sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4]))
write_new(Path(sys.argv[3])/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json',proof)
print(json.dumps({'status':proof['status'],'parents':proof['parents'],'scientific_values_emitted':False}))
"""


def prospective_analysis_argv(c,layout,expected,phase,work_deadline):
    """Reviewable command data only, NOT launch or authentication of a contract.

    Only the two implemented analysis steps are offered. Archive entry and the
    real frozen supervisor still require integration; no no-op archive command.
    """
    check_paths(layout);moment(work_deadline)
    if phase not in ('analysis','independent_acceptance'):raise ValueError('only implemented fixed analysis/independent-validator argv roles')
    if not isinstance(expected,str) or len(expected)!=64 or any(x not in '0123456789abcdef' for x in expected):raise ValueError('exact prospective contract SHA')
    source=layout['final_run']+'/source';task=layout['analysis_task'];contract=source+'/FINAL-CONTRACT.json'
    cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',source]
    read_only={layout['study_base'],source,c['venv'],c['renderer_path']}|{x['path'] for x in c['lewm'].values()}
    for p in sorted(read_only):cmd+=['--bind',p+':'+p+':ro']
    cmd+=['--bind',c['renderer_path']+':/renderer:ro','--bind',task+':'+task+':rw','--bind',task+'/tmp:/tmp:rw',
          c['sif'],c['venv']+'/bin/python','-B']
    if phase=='analysis':cmd+=['-m','wm_diag0_rc1_final_v1.analysis',contract,expected,task]
    else:cmd+=['-c',VALIDATE_CODE,contract,expected,task,str(work_deadline)]
    return cmd


def prospective_cpu_environment(parent,source):
    # Return a copy; never mutate the user's environment. Actual runtime/source
    # authentication and Slurm fourCPU/8GiB process-tree enforcement are separate.
    env={k:v for k,v in parent.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
    values={'PYTHONPATH':source,'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','CUDA_VISIBLE_DEVICES':'',
            'NVIDIA_VISIBLE_DEVICES':'void','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4',
            'NUMEXPR_NUM_THREADS':'4','LP_NUM_THREADS':'4','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
            'XFORMERS_DISABLED':'1','LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs',
            'MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe',
            'MESA_SHADER_CACHE_DISABLE':'true','SDL_VIDEODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1'}
    env['CUDA_VISIBLE_DEVICES']='';env['NVIDIA_VISIBLE_DEVICES']='void'
    env.update({'APPTAINERENV_'+k:v for k,v in values.items()});return env
