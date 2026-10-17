"""V2 CPU primitive: terminate owned group even after its leader exits.

No Slurm submission, actual analysis command, authorization or ready final
controller is provided by this module. A future authenticated controller must
bind all inputs, allocate the existing3600s/fourCPU/8GiB CPU stage and reserve
cleanup before using the runner. It never selects a command from artifact data.
"""
import os,queue,signal,stat,subprocess,threading,time
from pathlib import Path
from .archive_v1 import check_time
from .inventory import safe_name


PHASES=('analysis','independent_acceptance','archive','finalize')


def validate_design(grid,proposed):
    """Draft-only structure proof, not authentication of any required input."""
    if set(proposed)!=set(grid)|{'rc1_final'}:raise ValueError('only separately versioned final metadata may be added')
    for key,value in grid.items():
        if key!='staged_members' and proposed[key]!=value:raise ValueError('fixed grid science, suppliers and historical contracts unchanged')
    for name,x in grid['staged_members'].items():
        if proposed['staged_members'].get(name)!=x:raise ValueError('never replace an executed frozen source')
    new=set(proposed['staged_members'])-set(grid['staged_members'])
    for name in new:
        safe_name(name)
        if not name.startswith(('wm_diag0_rc1_final_v1/','final_evidence/')):raise ValueError('only new explicit final source/evidence closure')
    f=proposed['rc1_final']
    if f.get('analysis_authorized') is not False:raise ValueError('draft helper cannot grant research-analysis authority')
    if any(type(f.get(k)) is not int for k in ('allocation_seconds','CPUs','RAM_bytes','GPU_requested')) or type(f.get('automatic_retry')) is not bool:
        raise ValueError('exact integer CPU resource fields and boolean retry policy')
    if (f.get('allocation_seconds'),f.get('CPUs'),f.get('RAM_bytes'),f.get('GPU_requested'),f.get('automatic_retry'))!=(3600,4,8589934592,0,False):
        raise ValueError('unchanged finite CPU-only resource envelope and no retry')
    phase=f.get('phase_seconds',{})
    if set(phase)!=set(PHASES) or any(type(phase[k]) is not int or phase[k]<=0 for k in PHASES) or sum(phase.values())!=3600 or phase['finalize']<5:
        raise ValueError('full-future phase reservations including cleanup, no conversion-reserve borrowing')
    grid_root=Path(grid['run']);root=Path(f['run']);ops=Path(f['operational_root'])
    if not grid_root.is_absolute() or root!=grid_root.parent/'campaign-v4-rc1-final-v1' or ops!=grid_root.parent.parent/(grid_root.parent.name+'-rc1-preservation-v1'):
        raise ValueError('exact new final source root and disjoint operational preservation root')
    if Path(f['archive_path'])!=ops/'archive/final-study.tar':raise ValueError('archive outside every study input root')
    return {'status':'FIXED_SCIENCE_CPU_DRAFT_STRUCTURE_VALID_NOT_AUTHENTICATED','analysis_authorized':False,
            'CPU_full_future_seconds':1436+3600+1800,'conversion_seconds_consumed_or_reassigned':0,'phase_seconds':phase,
            'input_publication_SSD_runtime_historical_supplier_gates_checked':False,'final_gate_ready':False}


def artifact_bytes(roots):
    """Sample only own declared output/tmp roots; never follow redirects.

    This is an allocation-kill guard, NOT a hard filesystem quota. Final writers
    must also enforce their own finite pre-write output format bounds.
    """
    total=0
    for root in map(Path,roots):
        if root.is_symlink():raise ValueError('no artifact root redirect')
        if not root.exists():continue
        if not root.is_dir():raise ValueError('explicit artifact directory')
        for directory,dirs,names in os.walk(str(root),followlinks=False):
            if any((Path(directory)/n).is_symlink() for n in dirs):raise ValueError('no artifact directory symlink')
            for name in names:
                s=(Path(directory)/name).lstat()
                if not stat.S_ISREG(s.st_mode):raise ValueError('only bounded ordinary child artifacts')
                total+=s.st_size
    return total


def stop_owned(proc):
    # run_child always creates this process in a new session. A reaped leader
    # does NOT establish that its owned group is empty: descendants may still
    # hold the stdout pipe. Signal the owned POSIX group even after leader exit.
    if os.name=='posix':
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    elif proc.poll() is None:
        proc.kill() # artificial native tests have no descendants; real caller Linux/Slurm
    if proc.poll() is None:
        try:proc.wait(timeout=2)
        except subprocess.TimeoutExpired:raise RuntimeError('owned process cleanup deadline; external allocation limit still required')


def run_child(command,env,logpath,artifact_roots,artifact_cap,log_cap,work_deadline,cleanup_deadline):
    """One explicit trusted command, no shell and no automatic retry.

    The actual final controller must build a fixed CPU-only runtime command from
    reviewed source, not exported strings, and externally enforce process-tree
    memory/CPU. Work+cleanup are charged to the same allocation from entry.
    """
    if not isinstance(command,list) or not command or not all(isinstance(s,str) and '\x00' not in s for s in command):raise ValueError('explicit reviewed command argv')
    if type(artifact_cap) is not int or not 0<artifact_cap<=40000000 or type(log_cap) is not int or not 0<log_cap<=100000:raise ValueError('existing combined analysis-output/tmp and log bounds')
    if cleanup_deadline-work_deadline<2.2:raise ValueError('cleanup must be reserved, not added later')
    check_time(work_deadline);path=Path(logpath)
    if any(p.is_symlink() for p in path.parents):raise ValueError('no log parent redirect')
    q=queue.Queue(maxsize=2);stop=threading.Event();proc=None;thread=None;count=0
    def put(item):
        while not stop.is_set():
            try:q.put(item,timeout=.05);return
            except queue.Full:pass
    def pump():
        try:
            while not stop.is_set():
                raw=proc.stdout.read(8192)
                if not raw:put(('EOF',b''));return
                put(('DATA',raw))
        except BaseException as exc:put(('ERROR',repr(exc)))
    # Existing logs/partials cause refusal BEFORE launch; never truncate them.
    with path.open('xb') as log:
        try:
            if artifact_bytes(artifact_roots)>artifact_cap:raise ValueError('preexisting combined artifact bound')
            proc=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
            thread=threading.Thread(target=pump,name='wm-rc1-final-owned-child-log',daemon=True);thread.start()
            while True:
                check_time(work_deadline)
                if artifact_bytes(artifact_roots)>artifact_cap:raise ValueError('sampled combined artifact cap; preserve partials')
                try:kind,raw=q.get(timeout=min(.05,max(.001,work_deadline-time.monotonic())))
                except queue.Empty:continue
                if kind=='EOF':break
                if kind!='DATA' or not isinstance(raw,bytes):raise IOError('owned child log pipe failed: '+str(raw))
                if count+len(raw)>log_cap:raise ValueError('hard log byte limit; no excess bytes written')
                if log.write(raw)!=len(raw):raise IOError('short child-log write')
                log.flush();count+=len(raw)
            check_time(work_deadline)
            rc=proc.wait(timeout=max(.001,work_deadline-time.monotonic()))
            if rc:raise RuntimeError('trusted child exited '+str(rc)+'; no retry')
            if artifact_bytes(artifact_roots)>artifact_cap:raise ValueError('final combined artifact cap')
            log.flush();os.fsync(log.fileno());check_time(work_deadline)
            return {'status':'CHILD_COMPLETED_NOT_FINAL_ACCEPTANCE','returncode':rc,'log_bytes':count,
                    'artifact_bytes':artifact_bytes(artifact_roots),'automatic_retry':False,'final_gate_ready':False}
        finally:
            stop.set()
            if proc is not None:stop_owned(proc)
            if thread is not None:thread.join(timeout=.1)
            check_time(cleanup_deadline)
